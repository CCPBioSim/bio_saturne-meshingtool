"""Naming convention
_name = file name without path or extension
_filename = file name with extnesion but without path
_exten = file extnesion without .
_filepath = path to a file including filename and extension
_path = path to software"""

import sys
from datetime import datetime
import logging
import importlib
import subprocess as sp #Built in
import argparse
import re
import os
import math
import yaml
logging.getLogger('matplotlib').setLevel(logging.WARNING)

class LauncherError(Exception):
    '''Error handling when the a cmd is sent to the launcher
    function which results in an error'''
    def __init__(self, cmd, message):
        self.cmd = cmd
        self.message = '\n----------------Launcher Error----------------\n'\
        +cmd+'\n'+message
        super().__init__(self.message)

class NotFoundinFile(Exception):
    '''Error handling when a function searches for a term in a
    specific file'''
    def __init__(self, search_term, search_file, message=None):
        self.search_term = search_term
        self.search_file = search_file
        self.message = '\n----------------Not Found in File Error----------------\n'\
        +'Cannot locate '+search_term+' in file ' +search_file +'\n'+message
        super().__init__(self.message)

class SoftwareNotFound(Exception):
    '''Error handling when a specific software or software version
    isn't installed on the user's machine or exported to the path'''
    def __init__(self, software, version):
        self.software = software
        self.version = version
        self.message = '\n----------------Software Not Found Error----------------\n'\
        +"Please install "+ software +" version " + version + "+ or export it to $PATH"
        super().__init__(self.message)

class UnsupportedError(Exception):
    '''Error handling when the user configures the pipeline to use
    a file format or software which isn't currently supported'''
    def __init__(self, unsupported=None, supported=None):
        self.unsupported = unsupported
        self.supported = supported
        prt_supported = ', '.join(supported)
        self.message = '\n----------------Unsupported Error----------------\n'\
        +"We do not current support the " + unsupported + \
        " please try again using one of: "+ prt_supported
        super().__init__(self.message)

class InputError(Exception):
    '''Error handling when there is an error in a specific input
    argument'''
    def __init__(self, user_inp, message=None):
        self.user_inp = user_inp
        self.message = '\n----------------Input Error----------------\n'\
        +"Error with configured "+ user_inp +": "+ message
        super().__init__(self.message)

class CodeSaturneError(Exception):
    '''Error handling when CodeSaturne throws an error, which specifies
    which process in which the error has occured'''
    def __init__(self, process, message=None):
        self.process = process
        self.message = '\n----------------CodeSaturne Error----------------\n'\
        +"CodeSaturne error when" + process + ": " + message
        super().__init__(self.message)

class GmshError(Exception):
    '''Error handling when Gmsh throws an error, which specifies
    which process in which the error has occured'''
    def __init__(self, process, message=None):
        self.process = process
        self.message = '\n----------------Gmsh Error----------------\n'\
        +"Gmsh error when" + process + ": " + message
        super().__init__(self.message)

class ChimeraError(Exception):
    '''Error handling when Chimera throws an error, which specifies
    which process in which the error has occured'''
    def __init__(self, script, message=None):
        self.script = script
        self.message = '\n----------------Chimera Error----------------\n'\
        +"Chimera error: "+message+ " \nWhen executing the following script:\n" + script +\
        "\nThe file chimera_error.txt has more details"
        super().__init__(self.message)

logging.basicConfig(level=logging.DEBUG)
Logger = logging.getLogger('mesh-generator')

def exit_tool():
    '''Ends the program'''
    print("-----------END PROGRAM------------")
    sys.exit()

def write_launcher_err(launcher_err, cmd):
    '''Writes the entirity of the command output to a text file'''
    launcher_err = launcher_err.split('\n')
    now = datetime.now()
    time = now.strftime("%d%m%Y-%H%M%S")
    filename = 'cmd_err_'+time+'.txt'
    with open(filename, 'w') as lerr_file:
        lerr_file.write('\t\t Command Line Ouput\n')
        lerr_file.write('CMD: '+cmd+'\n\n')
        for le in launcher_err:
            lerr_file.write(le+'\n')
    return filename

def launcher(cmd, ig_error=False):
    '''Launches given commands on the command line
    Returns the error and output of the commands'''
    ind = 0
    lstdout = []
    lstderr = []
    if not isinstance(cmd[0], list):
        cmds = [cmd]
    else:
        cmds = cmd
    end = len(cmds)
    while ind < end:
        cur_cmd = cmds[ind]
        process_1 = sp.Popen(cur_cmd, stdout=sp.PIPE, stderr=sp.PIPE)
        stdout, stderr = process_1.communicate()
        #No error or want to parse the error
        if len(stderr.decode('utf-8')) == 0 or (ig_error and \
        len(stderr.decode('utf-8')) != 0):
            lstderr.append(stderr.decode('utf-8'))
            lstdout.append(stdout.decode('utf-8'))
            ind = ind + 1
        #The output is found in stderr
        elif ig_error and len(stdout.decode('utf-8')) == 0:
            lstderr.append(stdout.decode('utf-8'))
            lstdout.append(stderr.decode('utf-8'))
            ind = ind + 1
        else:
            error_file = write_launcher_err(stderr.decode('utf-8'), ', '.join(cur_cmd))
            raise LauncherError(' '.join(cur_cmd), \
            "\nPlease view the complete output in the file "+ error_file)
    if len(lstderr) == 1 and len(lstdout) == 1:
        lstderr = lstderr[0]
        lstdout = lstdout[0]
    return lstdout, lstderr

def has_number(string):
    '''Returns any number appearing in the given string'''
    return any(s.isdigit() for s in string)

def isnumber(num):
    '''Returns a Boolean value indicating
    whether the given 'num' is an int or float'''
    try:
        float(num)
        return True
    except ValueError:
        return False

def find_nodes_elements(outstr, log_file):
    '''Extracts the number of nodes and elements from the
    output of gmsh meshing'''
    ne_exp = re.compile(r'\d+ nodes \d+ elements')
    nodes_elements = ne_exp.findall(outstr)
    if nodes_elements == [] or len(nodes_elements) > 1:
        raise GmshError('generating a volumetric mesh', 'check the file '+log_file)
    n_exp = re.compile(r'\d+ nodes')
    e_exp = re.compile(r'\d+ elements')
    nodes = n_exp.findall(nodes_elements[0])
    elements = e_exp.findall(nodes_elements[0])
    return nodes[0]+' and '+elements[0]

def grep_software_path(soft_name):
    '''Grep for the given software in the bashrc to check for
    Its path if an alias is used'''
    home = os.environ['HOME']
    check_cmd = ['find', home + '/.bashrc']
    check_out, check_err = launcher(check_cmd, True)
    if 'No such file or directory' in check_out:
        return check_err
    grep_command = ['grep', soft_name, home + '/.bashrc']
    gc_out, gc_err = launcher(grep_command, True)
    if len(gc_err) == 0:
        return gc_out
    return gc_err

def which_software_path(soft_name):
    '''Attempts to find the software path using which'''
    which_path_cmd = ['which', soft_name]
    wp_out, wp_err = launcher(which_path_cmd)
    return wp_out

def find_software_ver(path):
    '''Finds the version of the given software'''
    if 'ccpem' in path:
        ver1 = re.findall(r'\.(\d)', path)
        ver2 = re.findall(r'(\d)\.', path)
        ver = list(dict.fromkeys(ver2+ ver1))
        ver = '.'.join(ver)
        return ver
    ver_cmd = [path, '--version']
    ver_out, ver_err = launcher(ver_cmd, True)
    if ver_out == "" and has_number(ver_err) and ('.' in ver_err):
        return ver_err
    if ver_out != "":
        return ver_out
    return ver_err

def input_software_path(software_name, version):
    '''Allows the user to input a path to the required software
    if the program cannot find it on their system'''
    enter_path = input("\nUnable to locate "+ software_name +
    " version " + version + "+ on your system\n Would you like to "
    "enter the path to this software on your system? (y/n): ")
    if enter_path.lower() == 'y':
        software_path = input("\nPlease enter the path to "
        + software_name + " version " + version + "+ :")
        check_path_cmd = ['find', software_path]
        check_path_out, check_path_err = launcher(check_path_cmd, True)
        if check_path_err != "":
            raise SoftwareNotFound(software_name, version)
        return software_path
    raise SoftwareNotFound(software_name, version)


def check_software_install(software_name, version):
    '''Performs checks on the installation of required software of the
    required version'''
    path = None
    which_software = which_software_path(software_name)
    if which_software != "" and which_software is not None:
        path = which_software
    else:
        grep_software = grep_software_path(software_name)
        path_exp = re.compile(r'.*="(.*/'+software_name+'.*)"')
        path = path_exp.findall(grep_software)
        if path == []:
            path = input_software_path(software_name, version)
        else:
            path = path[0]
    path = path.split(" ")[0]
    path = path.strip()
    current_version = find_software_ver(path)
    if current_version is None or not version in current_version:
        raise SoftwareNotFound(software_name, version)
    return path

def get_name_and_exten(filepath):
    '''Returns the name of a file and its extension from a given filepath'''
    filepath = filepath.replace('..', '')
    file_name = None
    file_exten = None
    if "/" in filepath:
        cut_ind = filepath.rfind('/')
        file_name = filepath[cut_ind+1:]
    else:
        file_name = filepath
    if '.' in file_name:
        exten_ind = file_name.find('.')
        file_exten = file_name[exten_ind+1:]
        file_name = file_name[:exten_ind]
    else:
        file_exten = 'emd'
    return file_name, file_exten

def extract_warnings(war_out):
    '''Extracts warning messages from the output of gmsh
    Note meshing is still considered successful even with warnings'''
    warn_ls = war_out.split('\n')
    wm_exp = re.compile(r'Warning : (.+)')
    warns = []
    count = 0
    while '------------------------------' not in warn_ls[count]:
        cur_warn = wm_exp.findall(warn_ls[count])[0]
        warns.append(cur_warn)
        count = count + 1
    return warns

def process_gmsh_error(err, out, input_name, log_path):
    '''Displays the errors and/or warnings from gmsh output when meshing'''
    en_exp = re.compile(r'(\d+) errors')
    wn_exp = re.compile(r'(\d+) warnings')
    err_num = en_exp.findall(err)
    war_num = wn_exp.findall(err)
    if len(err_num) != 1 and len(war_num) != 1:
        raise LauncherError('Meshing '+ input_name+' using gmsh', err)
    if err_num == []:
        err_num = 0
        war_num = int(war_num[0])
    elif war_num == []:
        err_num = int(err_num[0])
        war_num = 0
    else:
        err_num = int(err_num[0])
        war_num = int(war_num[0])
    #Uses the output to suggest why they may have occured
    if err_num > 0:
        message = '\nPlease see further details in '+log_path
        if 'A segment and a facet intersect at point' in err:
            message = 'Error suggests the mesh may have holes' + message
        if 'overlapping facets' in err and 'No elements in volume' in err:
            message = 'Error suggests the file contains unmeshable noise'
        raise GmshError(' generating the volume for '+ input_name, message)
    warnings = extract_warnings(err)
    warnings = ','.join(warnings)
    print("Warning: "+ warnings)
    cont = ""
    while cont not in ('y', 'n'):
        cont = input("Continue mesh generation? (y/n): ").lower()
    if cont == 'n':
        exit_tool()

def gmsh_from_stl(soft_dict, mesh_config_dict, input_filepath, input_name, log_foldr, \
mesh_filename, mesh_name):
    '''Performs volumetric meshing on an STL file using gmsh and a geo script file'''
    meshing_options = mesh_config_dict.keys()
    opts_lst = []
    for opt in meshing_options:
        if not opt in ['software', 'format', 'name']:
            opts_lst.append('-'+opt)
            opts_lst.append(str(mesh_config_dict[opt]))
    #Generates a logging folder in which to store any output from gmsh meshing command
    log_file = log_foldr +'/'+mesh_name + '_gmsh.log'
    geofile = make_geo(input_filepath, input_name)
    mesh_cmd = [soft_dict['gmsh'][1]]+ opts_lst+['-3', '-o', mesh_filename, '-format', \
    mesh_config_dict['format'], geofile, '-log', log_file]
    mesh_out, mesh_err = launcher(mesh_cmd, True)
    if mesh_err not in ("", None):
        process_gmsh_error(mesh_err, mesh_out, input_name, log_file)
    print("Volumetric mesh (", mesh_filename, ") generated with", \
    find_nodes_elements(mesh_out, log_file))
    mv_tmp_cmd = ['mv', geofile, '.tmp']
    launcher(mv_tmp_cmd)

def make_geo(stl_filepath, stl_filename):
    '''Writes a geo script to mesh with gmsh'''
    geofilename = stl_filename + '.geo'
    try:
        gfile = open(geofilename, 'w')
        gfile.write('Merge "' + stl_filepath + '";\n')
        gfile.write("Surface Loop(1) = {1};\n")
        gfile.write("Volume(1) = {1};\n")
        gfile.close()
    except OSError as exception:
        raise OSError(exception)
    return geofilename

def change_user_script(study_name, case_name):
    '''Changes CodeSaturne's user script to point to the input mesh located in the /MESH folder'''
    #Find line number of script which needs changing
    line_cmd = ['grep', '-n', 'domain.mesh_input = None', study_name+'/'+ case_name+\
    '/DATA/cs_user_scripts.py']
    line_out, line_err = launcher(line_cmd)
    line_num = re.match(r'.*?(\d*):(...[^#][^\d]*)\d*.*', line_out).group(1)
    #i.bak creates a backup of the original file
    sed_script = r's:domain.mesh_input = None:domain.mesh_input = "../MESH/mesh_input.csm":'
    sed_cmd = ["sed", "-i.bak", sed_script,
               study_name+'/'+ case_name+'/DATA/cs_user_scripts.py']
    sed_out, sed_err = launcher(sed_cmd)
    checksed_cmd = ['sed', '-n', r"%sp" % str(line_num), study_name+'/'+ case_name+\
    '/DATA/cs_user_scripts.py']
    checksed_out, checksed_err = launcher(checksed_cmd)
    #Checks file is successfully edited
    if 'domain.mesh_input = "../MESH/mesh_input.csm"' not in checksed_out:
        error_message = "Error setting domain.mesh_input = mesh_input.csm in "\
        +study_name+"/"+ case_name+"/DATA/cs_user_scripts.py\nPlease check the back-up file (/"\
        +study_name+"/"+case_name+"/DATA/cs_user_scripts.py.bak at line "+ line_num
        raise NotFoundinFile('domain.mesh_input = "../MESH/mesh_input.csm"', 'cs_user_scripts.py', \
        error_message)

def cs_generate_volume(cs_prepro_path, mesh_filename, log_foldr):
    '''Runs post-volume using CodeSaturne's preprocessor which outputs information on a
    given volumetric mesh'''
    mesh_name, mesh_exten = get_name_and_exten(mesh_filename)
    cs_cmd = [cs_prepro_path, '--log', log_foldr+'/'+mesh_name+'_cspreprocessor.log',
              '--post-volume', mesh_filename]
    cs_out, cs_err = launcher(cs_cmd, True)
    #Indicates the given mesh file is in 2D and has no volume
    if 'The mesh does not contain volume elements' in cs_out:
        raise CodeSaturneError('generating a volume', 'Ensure the mesh is defined in 3D')
    if cs_err != "":
        raise CodeSaturneError('generating a volume', '\n'+cs_err)

def cs_prepare_files(study_name, case_name, cs_path):
    '''Create a case and prepare the files and directories needed to run it'''
    #Create case
    case_cmd = [cs_path, 'create', '--study', study_name, case_name, '--copy-ref']
    #Create symbolic link to mesh file in /MESH
    symbl_cmd = ['ln', '-s', '-r', 'mesh_input.csm', study_name + '/MESH/']
    #Copy reference data into /DATA
    refd_cmd = ['cp', study_name +'/'+ case_name +'/DATA/REFERENCE/cs_user_scripts.py',
                study_name +'/'+ case_name +'/DATA/']
    launcher([case_cmd, symbl_cmd, refd_cmd])
    #Change script file to point at csm mesh assuming the first occurance of
    #'domain.mesh_input = None' is the line to change
    change_user_script(study_name, case_name)

def cs_run_quality(cs_path, study_name, case_name, wd_name):
    '''Run the quality check using CodeSaturne's preprocessor'''
    #Copy the /REFERENCE/cs_user_mesh.c into SRC folder
    cp_mesh_cmd = ['cp', study_name+'/'+ case_name+'/SRC/REFERENCE/cs_user_mesh.c',
                   study_name+'/'+ case_name+'/SRC']
    #Run the data preparation stage
    run_init_cmd = [cs_path, 'run', '--case', study_name+'/'+ case_name, '--id',
                    wd_name, '--initialize']
    #Run the solver
    run_solv_cmd = ['cs_solver', '-wdir', study_name+'/'+ case_name+'/RESU/'\
    +wd_name+'/', '--quality']
    #Check for run_solver.log file
    check_solv_cmd = ['ls', study_name+'/'+ case_name+'/RESU/'+wd_name+'/']
    solv_out, solv_err = launcher([cp_mesh_cmd, run_init_cmd, run_solv_cmd, check_solv_cmd])
    solv_files = solv_out[-1].split('\n')
    if not 'run_solver.log' in solv_files:
        raise CodeSaturneError('running cs_solver --quality', 'Check for the generation of'
        'run_solver.log when running cs_solver script in', study_name+'/'+ case_name+'/RESU/'
        +wd_name+'/')

def cs_prepro_quality(cs_prepro_path, cs_path, mesh_filename, log_foldr):
    '''Runs the steps required to generate a CodeSaturne case for the mesh and
    generate information on its quality'''
    mesh_name, exten = get_name_and_exten(mesh_filename)
    case_name = mesh_name +'_case'
    study_name = mesh_name + '_study'
    wd_name = mesh_name +'_quality'
    cs_generate_volume(cs_prepro_path, mesh_filename, log_foldr)
    cs_prepare_files(study_name, case_name, cs_path)
    cs_run_quality(cs_path, study_name, case_name, wd_name)
    quality_file = study_name+'/'+ case_name+'/RESU/'+wd_name+'/'+'run_solver.log'
    qual_foldr_cmd = ['mkdir', mesh_name+'_quality']
    cp_qual_cmd = ['cp', quality_file, mesh_name+'_quality/'+mesh_name+'_quality.log']
    launcher([qual_foldr_cmd, cp_qual_cmd])
    #run_solver.log contains the output of the quality check (post-volume)
    return mesh_name+'_quality/'+mesh_name+'_quality.log'


def extract_configs(yaml_file, input_exten, soft_dict):
    '''Extract the configuration arguments from the yaml file'''
    mesh_config_dict = {}
    map_config_dict = {}
    chi_config_dict = {}
    """Accepted configuration options and the input formats for which they apply to and the
    configuration dictionary they belong in (mesh, map or chi(mera))"""
    accepted_configs_dict = {'software':[['all'], 'mesh'], 'format':[['all'], 'mesh'],
                             'name':[['all'], 'mesh'], 'threshold':[['map', 'emd'], 'map'],
                             'dust_filter':[['map', 'emd'], 'map'],
                             'probe_radius': [['pdb'], 'chi'],
                             'grid_spacing':[['stl', 'pdb', 'map', 'emd'], 'chi']}
    loader = yaml.Loader
    meshing_soft = {}
    stream = open(yaml_file, 'r')
    try:
        user_config_dict = yaml.load(stream, Loader=loader)
    except yaml.YAMLError:
        raise InputError(yaml_file, "\nPlease check the contents of your yaml "
                         "configuration file \n(use http://www.yamllint.com/ to" 
                         " check for formatting errors)")
    user_configs = list(user_config_dict.keys())
    accepted_configs = list(accepted_configs_dict.keys())
    #Check the required configurations are provided
    if not set(['software', 'format']).issubset(user_configs):
        raise InputError("configurations", "\nPlease specify the meshing software'"
                         "and 'format' in the configuration file")
    #Check if any arguments in the configuration file aren't accepted
    diff = list(set(user_configs) - set(accepted_configs))
    if diff != []:
        diff = ', '.join(diff)
        raise InputError('configurations', '\nInvalid options in the configuration file: '+ diff)
    #Check the arguments given are valid for the given input format
    for uc in user_configs:
        if accepted_configs_dict[uc][0] != ['all'] and input_exten not in \
        accepted_configs_dict[uc][0]:
            raise InputError('configurations', "\nThe argument '"+uc+"' given in the"
                             " configuration file is not permitted for inputs of the format "
                             + input_exten)
        dict_name = accepted_configs_dict[uc][1]
        if dict_name == 'map':
            map_config_dict[uc] = user_config_dict[uc]
        elif dict_name == 'mesh':
            mesh_config_dict[uc] = user_config_dict[uc]
        else:
            chi_config_dict[uc] = user_config_dict[uc]
    meshing_soft[user_config_dict['software']] = [soft_dict[user_config_dict['software']][0]]
    return meshing_soft, mesh_config_dict, map_config_dict, chi_config_dict

def software_checks(soft_dict):
    '''Checks the required software is installed at the required version
    and updates the dictionary such that it now contains the path on the user's machine'''
    upd_soft_dict = {}
    for soft, ver in soft_dict.items():
        path = check_software_install(soft, ver[0])
        upd_soft_dict[soft] = [ver[0], path]
    return upd_soft_dict

def paraview_vis_surface(pv_path, mesh_filename):
    '''Launches the resultant mesh file in Paraview'''
    vis_mesh_cmd = [pv_path, mesh_filename]
    vis_mesh_out, vis_mesh_err = launcher(vis_mesh_cmd)

def extract_hist_data(data_lines, quality_file):
    '''Finds the frequency and upper and lower bounds of each histogram bin in the quality file'''
    bins = []
    freqs = []
    count = 0
    while count < len(data_lines):
        cur_freq = re.search(r"=.*(\d+)", data_lines[count]).group(1)
        freqs.append(int(cur_freq))
        bin_start = re.search(r"\[(.*);", data_lines[count]).group(1)
        try:
            val = float(bin_start)
        except:
            raise TypeError
        bins.append(val)
        if count == len(data_lines) -1:
            bin_end = re.search(r";(.*)[\]\[]", data_lines[count]).group(1)
            try:
                val = float(bin_end)
            except:
                raise TypeError
            bins.append(val)
        count = count + 1
    return bins, freqs

def format_title(lines, hist_count):
    '''Formats the titles of each histogram'''
    #Strips white space colons and indexing digits
    title = ''.join([l for l in lines[hist_count] if not (l.isdigit() or l == ':')])
    title = title.strip().split(' ')
    new_title = ' '.join(title[0:2])
    word_count = 2
    #Capitalises relevant title words
    while word_count < len(title):
        if not (title[word_count] == 'of' or title[word_count] == 'the'):
            new_title = new_title + ' ' + title[word_count].capitalize()
        else:
            new_title = new_title + ' ' + title[word_count]
        word_count = word_count + 1
    return new_title

def save_histogram(title, bins, freqs, mesh_name):
    '''Uses matplot lib to plot and save the histograms'''
    plt = importlib.import_module("matplotlib.pyplot")
    np = importlib.import_module("numpy")
    #Captures the output log of matplotlib so this isn't displayed
    plt_logger = logging.getLogger('matplotlib')
    Logger.setLevel(level=logging.DEBUG)
    fh = logging.StreamHandler()
    fh_formatter = logging.Formatter('%(asctime)s %(levelname)s \
    %(lineno)d:%(filename)s(%(process)d) - %(message)s')
    fh.setFormatter(fh_formatter)
    Logger.addHandler(fh)
    values = range(len(bins))
    #Represents the bin values as decimals
    exp, new_bins = decimal_representation(bins)
    freqs.insert(0, 0)
    widths = [-1] * (len(values) -1)
    widths.insert(0, 0)
    cur_fig = plt.bar(x=values, tick_label=new_bins, height=freqs, width=widths, align="edge");
    plt.xticks(fontsize = 6)
    plt.title(title);
    plt.ylabel('Frequency');
    plt.margins(x=0);
    #Implement superscripting
    if exp != 0:
        sup_script = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")
        sup_exp = str(exp).translate(sup_script)
        x_axis = ' '.join(title.split(' ')[3:]) + ' Factor (10' + sup_exp + ')'
    else:
        x_axis = ' '.join(title.split(' ')[3:])
    plt.xlabel(x_axis);
    file_name = mesh_name + '_'+title.replace(' ', '_') + '.pdf'
    plt.savefig(mesh_name+'_quality/'+mesh_name+'_histograms/'+file_name);
    plt.close();

def decimal_representation(floats):
    '''Returns a decimal representation of histogram bin bounds
    which are given in standard form'''
    new_floats = []
    min_flt = min(floats)
    if min_flt == 0:
        no_zero = [n for n in floats if n != 0]
        min_flt = min(no_zero)
    no_min = floats.copy()
    no_min.remove(min_flt)
    sec_min = min(no_min)
    if min_flt < 1 and sec_min / min_flt < 1000:
        recip = 1/min_flt
        log_ten = math.log(recip, 10)
        exp = math.ceil(log_ten)
    else:
        exp = 0
    for flt in floats:
        new_flt = flt*(10**exp)
        #Each value is approximated to 3 decimal places
        new_floats.append(float('%.3g' % new_flt))
    exp = exp*-1
    return exp, new_floats

def generate_histograms(quality_file, hist_title_lines, hist_start_lines,
                        hist_end_lines, mesh_name):
    '''Runs the functions required to create and save the histogram files'''
    hist_count = 0
    while hist_count < len(hist_title_lines):
        cur_start = hist_start_lines[hist_count]
        cur_end = hist_end_lines[hist_count]
        cur_title = format_title(hist_title_lines, hist_count)
        #Find the line numbers in the quality file where the data starts and ends
        start_line = re.search(r"(\d+):.*", cur_start).group(1)
        end_line = re.search(r"(\d+):", cur_end).group(1)
        #Get all file content between these lines which are the data to plot
        data_lines_cmd = ['sed', '-n', start_line+','+end_line+'p', quality_file]
        data_lines_out, data_lines_err = launcher(data_lines_cmd)
        data_lines = data_lines_out.split('\n')
        data_lines = data_lines[:-1]
        cur_bins, cur_freqs = extract_hist_data(data_lines, quality_file)
        save_histogram(cur_title, cur_bins, cur_freqs, mesh_name)
        hist_count = hist_count + 1

def remove_hist_without_data(hist_titles_out, hist_titles, hist_start_out, min_vals, max_vals):
    '''Prevents histograms without data from being plotted'''
    line_re = re.compile(r'(\d+):')
    title_lns = line_re.findall(hist_titles_out)
    start_lns = line_re.findall(hist_start_out)
    new_hist_titles = []
    new_mins = []
    new_maxs = []
    title_count = 0
    start_count = 0
    while title_count < len(title_lns):
        cur_start_ln = float(start_lns[start_count].replace('\n', ''))
        cur_title_ln = float(title_lns[title_count].replace('\n', ''))
        #All histograms with data have it 5 lines below their title
        if cur_start_ln == cur_title_ln + 5:
            start_count = start_count + 1
            new_hist_titles.append(hist_titles[title_count])
            new_mins.append(min_vals[title_count])
            new_maxs.append(max_vals[title_count])
        title_count = title_count + 1
    return new_hist_titles, new_mins, new_maxs

def remove_hist_min_max(hist_titles, min_vals, max_vals, hist_data_start, hist_data_end):
    '''Removes histogram data with 0 as the minimum and the maximum'''
    count = 0
    while count < len(hist_titles):
        if float(min_vals[count]) == 0 and float(max_vals[count]) == 0:
            hist_titles.pop(count)
            hist_data_start.pop(count)
            hist_data_end.pop(count)
        count = count + 1
    return hist_titles, hist_data_start, hist_data_end

def preprocess_hist_data(quality_file, mesh_name):
    '''Returns the lines in the file with important data for histogram generation'''
    #Finds the title lines
    hist_titles_cmd = ['grep', 'Histogram of', quality_file, '-n']
    hist_titles_out, hist_titles_err = launcher(hist_titles_cmd)
    hist_titles = hist_titles_out.split('\n')
    hist_titles.remove("")
    #Finds the start and end lines of the data
    hist_end_cmd = ['grep', r']', quality_file, '-n']
    hist_start_cmd = ['grep', r'1 : \[', quality_file, '-n']
    hstart_end_out, hstart_end_err = launcher([hist_start_cmd, hist_end_cmd])
    hist_data_start = hstart_end_out[0].split('\n')
    hist_data_end = hstart_end_out[1].split('\n')
    hist_data_start.remove("")
    hist_data_end.remove("")
    #Finds the lines of the maximum and minimum value of each histogram
    min_cmd = ['grep', 'minimum value = ', quality_file]
    max_cmd = ['grep', 'maximum value = ', quality_file]
    min_out, min_err = launcher(min_cmd)
    max_out, max_err = launcher(max_cmd)
    min_vals = min_out.replace('minimum value = ', '').strip().split('\n')
    max_vals = max_out.replace('maximum value = ', '').strip().split('\n')
    #Catches errors which may occur for the histogram data
    if len(hist_data_start) != len(hist_data_end):
        raise NotFoundinFile('an equal number of start and end data points for histograms', \
        quality_file)
    if len(min_vals) != len(max_vals):
        raise NotFoundinFile('an equal number of maximum and minimum values for histograms', \
        quality_file)
    if len(hist_titles) != len(min_vals):
        raise NotFoundinFile('maximum and minimum values for all histograms', quality_file)
    if len(hist_data_end) != len(hist_titles):
        hist_titles, min_vals, max_vals = remove_hist_without_data(hist_titles_out, hist_titles, \
        hstart_end_out[0], min_vals, max_vals)
    hist_titles, hist_data_start, hist_data_end = remove_hist_min_max(hist_titles, min_vals, \
    max_vals, hist_data_start, hist_data_end)
    return hist_titles, hist_data_start, hist_data_end

def process_cs_quality(quality_file, save_hist, mesh_name):
    '''Generates histograms if specified using the -hg flag'''
    if save_hist:
        print("\n----------HISTOGRAMS----------")
        hist_foldr_cmd = ['mkdir', mesh_name+'_quality/'+mesh_name + '_histograms']
        launcher(hist_foldr_cmd)
        hist_titles, hist_data_start, hist_data_end = preprocess_hist_data(quality_file, mesh_name)
        generate_histograms(quality_file, hist_titles, hist_data_start, hist_data_end, mesh_name)
        print("Histograms successfully generated and stored as pdfs in /"+mesh_name+'_quality/'\
        +mesh_name + '_histograms')

def make_logging_folder(mesh_name):
    '''Makes a logging directory for gmsh and CodeSaturne output'''
    log_foldr_cmd = ['mkdir', mesh_name+'_loggers']
    launcher(log_foldr_cmd)
    return mesh_name+'_loggers'

def mesh_filename_preexist(mesh_name, mesh_exten):
    '''Checks if the given name for the mesh file already exists in the current directory'''
    lsout, lserr = launcher(['ls'])
    mesh_filename = format_mesh_filename(mesh_name, mesh_exten)
    if mesh_filename in lsout:
        cont = ""
        #Allows the user to enter a new file name or overwrite the pre-exsisting file
        print("WARNING: File of the name", mesh_filename, "already exists in the"
        " current directory")
        cont = input("\nEnter 'y' to overwrite the file, 'n' to"
        " provide a new mesh file name or 'q' to quit: ")
        cont = cont.lower()
        while cont not in ('y', 'n', 'q'):
            cont = input("Please enter 'y', 'n' or 'q': ")
            cont = cont.lower()
        if cont == 'n':
            mesh_filename = input("Please enter a new file name: ")
        elif cont == 'q':
            exit_tool()
    return mesh_filename

def format_mesh_filename(mesh_name, mesh_exten):
    '''Replaces any spaces in the given filename with underscores and checks it doesn't
    include an extension'''
    mesh_filename = mesh_name.replace(' ', '_')
    if not '.' in mesh_name:
        mesh_filename = mesh_name+'.'+mesh_exten
    else:
        raise InputError('mesh name', "check the 'name' field in the configuration file"
        "(this name shouldn't include an extension)")
    return mesh_filename

def check_mesh_filename(mesh_name, mesh_exten, input_name):
    '''Checks the mesh filename'''
    #If it isn't provided the name of the input file is used partially
    if mesh_name is None:
        mesh_name = input_name + "_3d"
    #Then check if the file already exsists
    mesh_filename = mesh_filename_preexist(mesh_name, mesh_exten)
    return mesh_filename

def check_meshing_args(mesh_config_dict, supported_dict):
    '''Check the configurations provided for meshing are supported'''
    #Check the output format is supported
    if not mesh_config_dict['format'] in supported_dict['mesh_format']:
        raise UnsupportedError('configured mesh format', supported_dict['mesh_format'])
    if not mesh_config_dict['software'] in supported_dict['meshing_soft']:
        #Check the meshing software is supported
        raise UnsupportedError('configured meshing software', supported_dict['meshing_soft'])

def check_input_args(input_format, inp, supported_input, soft_dict):
    '''Check the input argument'''
    #Check the format of the input file is supported
    if input_format not in supported_input:
        raise UnsupportedError('input file format', input_format)
    #Check for emd entries that the input is given in the format emd_{entry number}
    if input_format == 'emd':
        format_chk = bool(re.match(r'emd_\d+', inp))
        integer_chk = inp.isdigit()
        if not (format_chk or integer_chk):
            raise InputError('emd entry', "\n"+r"Please enter the input in the format:"
            r" emd_{entry number} e.g. emd_3066")
    else:
        input_name, input_exten = get_name_and_exten(inp)
        #Check the format of the input file matches the format argument given
        if input_exten != input_format:
            raise InputError('input file', '\nPlease ensure the input file is saved with'
            ' the appropriate extension specified in --format')
    #Add extra software requirements for map cleaning and generating an stl
    if input_format in ('map', 'emd'):
        soft_dict['ucsf-chimerax'] = ['1.3']
        soft_dict['ccpem'] = ['1.5']
    elif input_format == 'pdb':
        soft_dict['ucsf-chimerax'] = ['1.3']
    if input_format != 'msh':
        soft_dict['gmsh'] = ['4.8']
    return soft_dict

def clean_directory(mesh_name, ini_dir):
    '''Move any folders/files that weren't initially in the directory to .tmp'''
    ls_cmd = ['ls']
    ls_out, ls_err = launcher(ls_cmd)
    ls_out = ls_out.split('\n')
    mesh_cont = [c for c in ls_out if mesh_name in c and not '_study' in c]
    keep = ini_dir + mesh_cont
    mv_fldrs = [c for c in ls_out if (not c in keep) and (c != "")]
    for mv_fldr in mv_fldrs:
        mv_tmp_cmd = ['mv', mv_fldr, '.tmp']
        launcher(mv_tmp_cmd)

def download_emd(emd):
    '''Use rsync to download the map file from EMDB'''
    print("------------DOWNLOADING EMD FILE--------------")
    if emd.isdigit():
        entry_num = int(emd)
    else:
        num_re = re.compile(r'emd_(\d*)')
        entry_num = num_re.findall(emd)[0]
    emd_cmd = ['rsync', '-rlpt', '-v', '-z', '--delete',
               'rsync.ebi.ac.uk::pub/databases/emdb/structures/EMD-' \
    +str(entry_num)+'/map', './EMD-'+str(entry_num)]
    mv_emd_cmd = ['cp', 'EMD-'+str(entry_num)+'/map/emd_'+str(entry_num)+'.map.gz', '.']
    #Unzip the downloaded compressed map file
    unzip_cmd = ['gunzip', 'emd_'+str(entry_num)+'.map.gz']
    launcher([emd_cmd, mv_emd_cmd, unzip_cmd])
    map_filename = 'emd_'+str(entry_num)+'.map'
    print(map_filename + " successfully downloaded\n")
    return map_filename

def ccpem_cleaning(ccpem_path, map_filepath, map_name, map_config_dict):
    '''Perform map cleaning using CCPEM toolkit'''
    config_cmd = []
    map_configs = map_config_dict.keys()
    for config in map_configs:
        #Check dust_filter argument given is a bool and add the command to perform this
        if config == 'dust_filter':
            if map_config_dict[config].lower() == 'true':
                config_cmd = config_cmd + ['-l', 'dust_filter']
            elif map_config_dict[config].lower() != 'false':
                raise InputError('configurations', "\nInvalid value for argument"
                "'dust_filter' in the configuration file. This must be True or False")
        #Check threshold argument given is a number and add the command to perform this
        if config == 'threshold':
            if isnumber(map_config_dict[config]):
                config_cmd = config_cmd + ['-t',
                                           str(map_config_dict[config])]
            else:
                raise InputError('configurations', "\nInvalid value for argument 'threshold'"
                "in the configuration file. This must be an integer or float")
    ccpem_cmd = ['ccpem-python', ccpem_path[0:-10]+ \
    'lib/py2/ccpem/src/ccpem_core/map_tools/TEMPy/map_preprocess.pyc', '-m', map_filepath] \
    + config_cmd + ['-out', map_name +'_cleaned.map']
    launcher(ccpem_cmd)
    #Return the cleaned map name
    return map_name+'_cleaned.map'

def process_chi_error(chi_err, cxc_filename):
    '''Extracts relevant information to raise a ChimeraError'''
    #Read the chimera script to display to the user
    cxc_script = ""
    with open(cxc_filename, 'r') as cxc_file:
        eof = False
        while not eof:
            cur_line = cxc_file.readline()
            if cur_line == '':
                eof = True
            else:
                cxc_script = cxc_script + '\t'+cur_line
    #Find output which has readble error messages
    err_exp = re.compile(r'Error: (.*)')
    try:
        main_err = err_exp.findall(chi_err)[0]
    except:
        main_err = ""
    chi_err = chi_err.split('\n')
    chi_filename = 'chimera_error.txt'
    with open(chi_filename, 'w') as chi_file:
        for chi_ln in chi_err:
            chi_file.write(chi_ln + '\n')
    raise ChimeraError(cxc_script, main_err)

def to_stl(chimera_path, filepath, name, exten, chi_config_dict):
    '''Convert the given file to an STL using ChimeraX'''
    print("------------CONVERTING TO STL------------")
    cxc_filename = name+"_chimerax_script.cxc"
    chi_configs = chi_config_dict.keys()
    cxc_file = open(cxc_filename, 'w')
    cxc_file.write("log hide\n")
    cxc_file.write(f"open {filepath}\n")
    #PDB files require a probe radius to generate a surface
    if 'probe_radius' not in chi_configs and exten == 'pdb':
        raise InputError('configurations', "\nPlease provide a value for 'probe_radius'"
        " in the configuration file when using a pdb input")
    #Check other chimera scripting arguments given are numbers
    for cc in chi_configs:
        if not isnumber(chi_config_dict[cc]):
            raise InputError('configurations', "\nInvalid value for argument '"+cc+"' in the"
            " configuration file. This must be an integer or float")
        if cc == 'probe_radius':
            cxc_file.write(f"surface probeRadius {chi_config_dict[cc]}\n")
            #Ribbon representations of pbd files must be hidden or they create an inner surface
            cxc_file.write("hide all\n")
            cxc_file.write("~ribbon\n")
        else:
            cxc_file.write(f"surface gridSpacing {chi_config_dict[cc]}\n")
    cxc_file.write(f"save {name}.stl\n")
    cxc_file.write("quit")
    cxc_file.close()
    #Run the script with no gui and offscreen logging
    chi_cmd = [chimera_path, '--nogui', '--offscreen', '--exit', cxc_filename]
    chi_out, chi_err = launcher(chi_cmd, True)
    if chi_err != "":
        process_chi_error(chi_err, cxc_filename)
    mv_tmp_cmd = ['mv', cxc_filename, '.tmp']
    launcher(mv_tmp_cmd)
    print("Successfully generated "+ name + ".stl\n")
    return name

def get_initial_dir():
    '''Lists all the files initially in the directory before running the pipeline'''
    ini_dir = []
    ls_cmd = ['ls', '-a']
    ls_out, ls_err = launcher(ls_cmd)
    ini_dir = ls_out.split('\n')
    ini_dir = [i for i in ini_dir if i != ""]
    #Checks if there is already a hidden tmp directory
    if '.tmp' in ini_dir:
        print("Hidden directory .tmp already exists in the directory (from a previous run)\n"
        "If you want to retain this directory please rename it appropriately and"
        "start this run again")
        ask = True
        while ask:
            overwrite = input("Overwrite this directory (y/n): ")
            if overwrite.lower() == 'y':
                rm_tmp_cmd = ['rm', '-r', '.tmp']
                launcher(rm_tmp_cmd)
                ask = False
            elif overwrite.lower() == 'n':
                ask = False
                exit_tool()
    return ini_dir

def main():
    initial_contents = get_initial_dir()
    meshing_soft = {}
    #CodeSaturne is the only software required for any input format
    base_softs = {
        'code_saturne': ['7.0'],
        'cs_preprocess': ['7.0'],
        }
    #All supported formats and softwares which may be given as arguments
    supported_dict = {
        'meshing_soft': ['gmsh', 'salome'],
        'input_format':['stl', 'map', 'emd', 'msh', 'pdb'],
        'mesh_format':['msh']
    }
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", required=True, help="path to the input file")
    parser.add_argument("-f", "--format", required=True, help="format of the input file")
    parser.add_argument("-c", "--configs", required=False, help="file name (and path) to "
    "configuration yaml file")
    #Histograms and visualisation are optional flags
    parser.add_argument("-hg", "--histograms", required=False, help="flag to generate "
    "histograms to assess mesh quality", action="store_true")
    parser.add_argument("-v", "--visualise", required=False, help="Generates a "
    "visualisation of the surface in Paraview", action='store_true')
    args = parser.parse_args()

    #Generate a software dictionary with all the baseline required software
    soft_dict = base_softs.copy()

    #Check all arguments and configurations are supported for the input
    #Update the software dictionary depending on required software for specific input formats
    #e.g. ChimeraX for emd and map inputs
    soft_dict = check_input_args(args.format, args.input, supported_dict['input_format'], soft_dict)
    input_filepath = '../'+args.input
    #For emd entry inputs, the input name is emd_{entry number} and extension is emd
    input_name, input_exten = get_name_and_exten(input_filepath)
    #Check the meshing configurations if provided
    if args.configs is not None:
        #Extract configs from yaml and update required software dictionary
        meshing_soft, mesh_config_dict, map_config_dict, chi_config_dict = \
        extract_configs(args.configs, input_exten, soft_dict)
        soft_dict.update(meshing_soft)
        check_meshing_args(mesh_config_dict, supported_dict)
        #Format/verify the mesh filename
        if 'name' in mesh_config_dict:
            mesh_filepath = check_mesh_filename(mesh_config_dict['name'],
                                                mesh_config_dict['format'],
                                                input_name)
        else:
            mesh_filepath = check_mesh_filename(None, mesh_config_dict['format'], input_name)
    else:
        #Meshing configurations are only not provided when the input
        #Is a mesh itself
        mesh_filepath = '../'+args.input

    #If the visualisation flag is enabled add paraview to the software dictionary
    if args.visualise:
        soft_dict['paraview'] = ['5.7.0']

    #Check all the required software is installed to run the pipeline
    soft_dict = software_checks(soft_dict)

    #Extract the mesh name from the filepath
    mesh_name, mesh_exten = get_name_and_exten(mesh_filepath)

    #Make the run directory in which to store all other files
    now = datetime.now()
    date_time = now.strftime("_%d%m%Y_%H%M%S")
    run_directory = mesh_name + date_time
    runcmd = ['mkdir', run_directory]
    launcher(runcmd)

    #Change to the run directory so all subsequent files are stored here
    os.chdir(run_directory)

    #Make hidden directory to store temporary files
    tmpcmd = ['mkdir', '.tmp']
    launcher(tmpcmd)
    #Make the logging folder for all log files during pipeline
    log_foldr = make_logging_folder(mesh_name)

    #Handles emd entry number and map file inputs
    if input_exten in ("emd", "map"):
        if input_exten == 'emd':
            map_filepath = download_emd(input_name)
        elif input_exten == 'map':
            map_filepath = '../'+input_filepath
        #Filters map and converts the format to stl
        map_name, map_exten = get_name_and_exten(map_filepath)
        if map_config_dict != {}:
            map_filepath = ccpem_cleaning(soft_dict['ccpem'][1], map_filepath, map_name,
                                          map_config_dict)
        input_name = to_stl(soft_dict['ucsf-chimerax'][1], map_filepath, map_name, map_exten,
                            chi_config_dict)
        input_exten = 'stl'
        input_filepath = input_name + '.' + input_exten
    elif input_exten == 'pdb':
        pdb_name, pdb_exten = get_name_and_exten(input_filepath)
        #Generates a surface for the pdb and converts this to an STL using Chimera
        input_name = to_stl(soft_dict['ucsf-chimerax'][1], input_filepath, pdb_name, 'pdb',
                            chi_config_dict)
        input_exten = 'stl'
        input_filepath = input_name + '.' + input_exten

    #Handles STL file on input or from conversion
    if input_exten == "stl":
        #Handles meshing STL files using gmsh
        if mesh_config_dict['software'] == 'gmsh':
            print("----------------GMSH----------------")
            gmsh_from_stl(soft_dict, mesh_config_dict, input_filepath, input_name, log_foldr,
                          mesh_filepath, mesh_name)
        #Handles meshing STL files using Salome
        elif mesh_config_dict['software'] == 'salome':
            print("salome")

    #Run Quality Checks on resultant mesh_filepath
    print("\n----------------CODESATURNE----------------")
    quality_file = cs_prepro_quality(soft_dict['cs_preprocess'][1], soft_dict['code_saturne'][1],
                                     mesh_filepath, log_foldr)
    print("CodeSaturne quality assessment complete.\nFile located: "+ quality_file +"\n")

    #If histogram flag is given then save data in histogram form for the mesh
    if not args.histograms:
        save_hist = False
    else:
        save_hist = True
    process_cs_quality(quality_file, save_hist, mesh_name)

    #Clean the directory by moving any intermediate files/folders to .tmp
    print("-----------------CLEAN-------------")
    clean_directory(mesh_name, initial_contents)
    print("\nFurther files generated by intercalated software is stored in "
          +run_directory+"/.tmp")
    exit_tool()


try:
    main()
except Exception as e:
    logging.error(traceback.format_exc())
    exit_tool()
else:
    print("Unexpected Error Occurred")
