# oceancontour-docker
OceanContour is proprietary software developed by Nortek for ADCP data-processing.
Although it has a rudimentary cli, it is formost a graphical program which will balk if it cannot output to a display. 
This makes it difficult to include in an automated a processing pipeline. 

This repo dockerizes OceanContour by internally creating a virtual display environment using Xvfb, and by pre-configuring necessary files and directories typically set up during graphical use.

## LICENCING
In order to process files, OceanContour requires your software to associated with an activated licenced. Assuming you have purchased a licence from Nortek, you can activate your licence for oceancontour-docker using the following steps: 
 1. launching `Oceancontour-gui.sh bash`
 2. running `OceanContour`
 3. following Nortek's licence activation steps
 4. once your licence is activated, close OceanContour. You should be back in the container's shell
 5. Copy the licence file out of the container: `cp ~/OIContour/.metadata/OceanContour.lic vol/`
 6. Add the extracted licence into your docker images or containers
    * build a new image with the licence: `built -t oceancontour --build-arg LICENCE your/OceanContour.lic .`
    * mount your licence into your containers at runtime by editing the .sh files with `-v your/OceanContour.lic:/root/OIContour/.metadata/OceanContour.lic`

 NOTE: Licences are validated against your "hardware". When activated in a docker container, one of the variables it listens to is your containers *hostname*. Once you have activated a licence, make sure that your subsequently run containers have the same hostname. This repo's scripts when doing `docker run` consistently defaults to using `-h oceancontour-container` for this reason.

## Scripts
- `OceanContour-auto.sh` - Accepts 3 parameters: rawdata file, parameter file, target output .nc file
- `OceanContour-combo.sh` - Accepts 4 parameters: rawdata file, wave parameter file, burst/current averaging parameter file, target combined .nc output file
- `OceanContour-gui.sh` - container with X11 socket passthrough and workspace volume mount. Allows OceanContour to be displayed graphically on your screen. (Linux Only)
- `OceanContour-sshXgui.sh` - PENDING as above, but for when using `ssh -X` to access the docker host machine. 




