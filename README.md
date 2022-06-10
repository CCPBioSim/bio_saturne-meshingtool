# BioSaturne Pipeline
The BioSaturne Pipeline is a chain of pre-exsisting software tools
linked together to create an unstructured volumetric mesh, which can
then be used in a BioSaturne or FFEA simulation.
It can also be used to quality check a (pre-exsisting)
mesh using code_saturne capabilities.

The pipeline has been developed to run on Linux machines.

## Supported Input Formats
The BioSaturne Pipeline supports the following input formats
- [STL](#from-stl) (.stl) 
- [PDB](#from-pdb) (.pdb)
- [Cryo-EM Map](#from-emdmap) (.map)
- [Mesh](#from-msh) (.msh)
- [EMDB Entry Number](#from-emdmap) (emd_{entry number})

## Installation
To install and use the program simply download [```bio_saturne-meshingtool.py```](https://github.com/CCPBioSim/bio_saturne-meshingtool/blob/main/bio_saturne-meshingtool.py) from the repository.
This can be done by following the link to the program on GitHub, clicking Raw and then saving the
program locally.

Please refer to the installation requirements below before running the program.

## Installation Requirements
All intended uses of the pipeline requires
- [code_saturne](https://www.code-saturne.org) (ver 7.0.0+)

If you are running the pipeline to perform a quality check on a pre-exsisting mesh, this is 
the only software you are required to install.

Additional software requirements depend on the format of the input, as shown below.
You must install the software on your system accordingly, depending on your intended use, before running
the pipeline unless they have been installed previous.

The pipeline will check that software has been installed centrally, or alternatively that
they have been added to $PATH.

| Software                                                                               | Input Format        |
| ---------------------------------------------------------------------------------------| --------------------|
| <a href="https://gmsh.info" target=”_blank”>Gmsh</a> (ver 4.10.2+)                     | stl, pdb, map, emd  |
| <a href="https://www.cgl.ucsf.edu/chimerax/" target="_blank">ChimeraX</a> (ver 1.3+)   | pdb, map, emd       |
| <a href="https://www.ccpem.ac.uk/download.php" target="_blank">CCP-EM</a> (ver 1.5.0+) | map, emd            |



The pipeline has been developed in Python 3.8 and therefore requires Python3 to 
run. It also depends on the following python modules, all of which can be installed 
using pip.

- [PyYAML](https://pypi.org/project/PyYAML/)     
- [Matplotlib](https://pypi.org/project/matplotlib/)
- [Argparse](https://pypi.org/project/argparse/)      
- [Numpy](https://pypi.org/project/numpy/)

## Command-line Options
- ``` -i ``` The input file (including the path if it is not in the current directory).
- ``` -f ``` The format of the input file e.g. stl, emd, pdb or map.
- ``` -c ``` The [configuration](#configuration-file) yaml file (including the path if it is not in the current directory).
- ``` -hg ``` Optional flag to determine whether you want to generate [histograms](#output) based on data of the meshes quality (code_saturne).

## Configuration File
A configuration file (.<a href="https://docs.fileformat.com/programming/yaml/" target=”_blank”>yaml</a>) is required for all input formats, excluding a pre-exsisting mesh (.msh).

Inside the file you can specify parameters for meshing, cleaning (using CCP-EM's toolkit) and refining the STL file
(using ChimeraX). The parameters are listed below, and those that are required are marked as such.

- ```software```<span style ="color:red;">*</sup></span> The meshing software to generate the mesh.
- ```format```<span style ="color:red;"><sup>*</sup></span> The format of the mesh you wish to generate.
- ```name``` The filename for the resulting mesh (excluding the extension). If not provided then the
mesh file will be saved as '{input file name}_3d'.
- ```threshold``` Contour threshold for electron density map cleaning using CCP-EM.
- ```dust_filter``` Boolean value to indicate the use of CCP-EM's dust filter during map cleaning.
- ```probe_radius```<span style ="color:red;"><sup>**</sup></span> The radius of the probe in Angstroms (Å) used in ChimeraX to generate a surface<sup>[1]</sup>.
- ```grid_spacing``` Define the spacing in Angstroms (Å) for the surface in ChimeraX, which by default is 0.5 Å. Smaller grid spacing values
give a smoother surface and therefore STL<sup>[1]</sup>.

[1]:  https://www.cgl.ucsf.edu/chimerax/docs/user/commands/surface.html

<font size="1"><span style ="color:red;">*</sup></span>*Required* &nbsp; <span style ="color:red;">**</sup></span>*Required for pdb input*</font>

## Output
Once the pipeline is complete the current directory will have the following structure and contents:
```
local_directory
│   input_file
|
└───mesh_name_date_time
    │   mesh_file
    |   .tmp
    │
    └───mesh_name_loggers
    │       │   meshing_software.log   
    │       │   code_saturne_preprocessor.log
    │   
    └───mesh_name_quality
        │   mesh_name_quality.log
        └───mesh_name_histograms
```
The **loggers directory** will contain the logging files generated by the meshing software and code_saturne. The **quality directory** will contain the file generated by code_saturne, with information about the mesh and data related to its quality. 

**.tmp** is a hidden directory created to store all intermediate files, such as STUDY and CASE directories for code_saturne and geo and stl files for mesh generation.

### Histograms
If ``` -hg ``` is used when running the pipeline, the histograms directory 
is created. This contains histogram pdf files which are generated from the data in the quality log. They describe on various aspects of the mesh, as listed below.
* Boundary Cell Thickness
* Cell Volume
* Cells Off-Centering Co-efficient
* Cellwise Warping Error
* Number of Interior Faces per Cell
* Boundary and Interior Faces
  * Non-orthoganality Co-efficient
  * Warping
  * Weighting Co-efficient

## Examples
- ## From EMD/Map
  Map file and EMDB entry inputs are ran using a similar command. However for maps, the file must pre-exist on your local machine, whereas EMD only requires an entry number and will download the map for you.

  In the examples below, the EMBD entry number 26222 corresponds to the 3D structure of GroEL protein compelxes<sup>[2]</sup>.

  **From EMD**
  ``` sh
  bio_saturne-meshingtool.py -i 26222 -f emd -c 26222_configs.yaml
  ```

  **From Map**
  ``` sh
  bio_saturne-meshingtool.py -i emd_26222.map -f map -c 26222_configs.yaml
  ```

  **26222_configs.yaml** contains the following lines:

  ``` yaml
    software: "gmsh"
    format: "msh"
    name: "26222_mesh"
    threshold: 0.154
    dust_filter: "true"
  ```
  <font size="1">**Note**: If you are implementing thresholding, you can sometimes find a suggested value ('Recommended contour level') under the Validation tab of the entry on [EMDB](https://www.ebi.ac.uk/emdb/).</font>

  3D surface of EMD-26222 from EMDB<sup>[2]</sup> |  Paraview visualisation of 26222_mesh.msh
  :----------------------------------------------:|:-------------------------:
  ![](./imgs/26222_emd.jpeg)                       |  ![](./imgs/26222_pv.jpeg)

  [2]:  https://www.ebi.ac.uk/emdb/EMD-26222


- ## From PDB
  ``` sh
  bio_saturne-meshingtool.py -i 7Q0T.pdb -f pdb -c lysozyme_configs.yaml
  ```
  **lysozyme_configs.yaml** contains the following lines:
  ``` yaml
   software: "gmsh"
   format: "msh"
   name: "lysozyme_mesh_pr2_gs2"
   probe_radius: 2
   grid_spacing: 1
  ``` 

  3D view of 7Q0T from PDB<sup>[3]</sup> |  Paraview visualisation of lysozyme_mesh_pr2_gs2.msh
  :-------------------------------------:|:-------------------------:
  ![](./imgs/pdb_lys_pdb.jpeg)           |  ![](./imgs/pdb_lys_2_1.jpeg)

  [3]:  https://www.rcsb.org/structure/7Q0T

  Below are two further examples using the same pdb file but different values for the **probe_radius** and **grid_spacing**<sup>[4]</sup>. 

  [4]:  https://www.cgl.ucsf.edu/chimerax/docs/user/commands/surface.html#sop
  
  By comparing the images below to the one above, increasing the **grid_spacing** decreases the fineness of the mesh and increasing the **probe_radius** increases the smoothness of the surface.

  probe_radius: 5, grid_spacing: 1 |  probe_radius: 2, grid_spacing: 2
  :-------------------------------:|:---------------------------------:
  ![](./imgs/pdb_lys_5_1.jpeg)     |  ![](./imgs/pdb_lys_2_2.jpeg)

  <font size = "1">**Note**: When choosing the best values for **probe_radius** and **grid_spacing** it may be more appropriate to, initially, visualise the changes in ChimeraX's GUI.</font>

- ## From STL
  ``` sh
  bio_saturne-meshingtool.py -i sphere.stl -f stl -c sphere_configs.yaml
  ```
  **sphere_configs.yaml** contains the following lines:
  ``` yaml
   software: "gmsh"
   format: "msh"
   name: "sphere_mesh"
  ``` 
  When using an STL file as input to the pipeline, the meshing software will use the triangles present on the surface to generate an internal volume. The surface may not be re-triangulated.

  STL                               |   MSH
  :--------------------------------:|:-------------------------------------:
  ![](./imgs/stl_sphere.jpeg)       |  ![](./imgs/stl_sphere_mesh.jpeg)
  

- ## From MSH
  ``` sh
  bio_saturne-meshingtool.py -i 25408.msh -f msh -hg 
  ```
  Running the pipeline from msh uses code_saturne capabilities to perform a quality check on the pre-existing mesh.
  As mentioned previously, the histogram flag (```-hg```) is optional. All data can instead be found in the file ```mesh_name_quality.log```.

    25408_msh<sup>[5]</sup>         |   Histogram
  :--------------------------------:|:-------------------------------------:
  ![](./imgs/msh_25408.jpeg)        |  ![](./imgs/msh_25408_hist.jpeg)

  The histogram on the right is just one example of the histograms generated from code_saturne's quality criterea. All values shown on the axis are rounded to 3 s.f (significant figures).

  [5]:  https://www.ebi.ac.uk/emdb/EMD-25408