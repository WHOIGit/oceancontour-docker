#! /usr/bin/env python

import os
import sys
import shutil
import logging
import argparse

import h5py
from pyvirtualdisplay import Display
from easyprocess import EasyProcess

LOGGER = logging.getLogger()
WORKSPACE='/app/workspace'
PROJECT='project1'
EXPORT_DIR='/app/EXPORT'



def generate_section_autonomous(project, export_dir, filetype='Burst'):
    section = f'''
Section Autonomous
File Type: {filetype}
Export NetCDF: {export_dir}
Project: {project}
'''
    return section



def paramfile_overwrite_sectionautonomous(paramfile_in, paramfile_out, project, export_dir, filetype='Burst'):
    # makes a copy of paramfile to project_dir with appended "Section Autonomous".
    # if Section Autonomous already in the file, it will be overwritten if overwrite=True
    
    with open(paramfile_in) as f:
        param_content = f.read()
    
    section_autonomous = generate_section_autonomous(project, export_dir, filetype)
    with open(paramfile_out, 'w') as f:
        f.write( param_content.split('Section Autonomous')[0] )
        f.write(section_autonomous)
    
    return os.path.realpath(paramfile_out)



def rawfile_checkfor_header(rawfile_in, rawfile_out=None, headerfile=None):
    # TODO test this works
    if rawfile_out is None:
        rawfile_out = os.path.splitext(rawfile_in)[0]+'.auto'
    HEADTAG = b'\xa5\n\xa0\x10\xc5\x0f\x14\xe6\xaa\xc6\x10GETCLOCKSTR'
    with open(rawfile_in, 'rb') as f:
        headtag = f.read(len(HEADTAG))
    if headtag == HEADTAG or headerfile is None:
        shutil.copyfile(rawfile_in, rawfile_out)
    else:  # header is missing
        with open(rawfile_in, 'rb') as fin, open(rawfile_out, 'wb') as fout, open(headerfile, 'rb') as fhead:
            shutil.copyfileobj(fhead, fout)
            shutil.copyfileobj(fin, fout)
    return rawfile_out
    


def expected_nc_filename(paramfile):
    sections = []
    filetype = ''
    with open(paramfile) as f:
        for line in f:
            if line.startswith('File Type:'):
                filetype = line.split(':')[1].strip()
            elif line.startswith('Section'):
                section = line.split(maxsplit=1)[1].strip()
                if section == 'Autonomous': continue
                sections.append( section )
    
    mappings = {'Transform and Correction':'VTC',
                'Wave Processing':'WAVES',
                'Data Selection':'DSEL',
                'Averaging':'AVER'}
    
    fname = f'{filetype}_001.{".".join([mappings[section] for section in sections])}.nc'
    return fname



def nc_combo(wave_nc, curr_nc, combo_nc ):
    LOGGER.info(f'COMBINING {os.path.basename(wave_nc)} and {os.path.basename(curr_nc)} into single hdf: {os.path.basename(combo_nc)}')
    with h5py.File(wave_nc, 'r') as wave_nc, h5py.File(curr_nc, 'r') as curr_nc, h5py.File(combo_nc, 'w') as combo_nc:
        # CONFIG
        LOGGER.info("Collating nc['Config'].attrs attributes")
        att_curr = set(curr_nc['Config'].attrs)
        att_wave = set(wave_nc['Config'].attrs)

        LOGGER.debug('Unique to AVG:')
        unq_curr = att_curr - att_wave
        LOGGER.debug(' '.join(sorted(unq_curr)))

        LOGGER.debug('\nUnique to Wave:')
        unq_wave = att_wave - att_curr
        LOGGER.debug(' '.join(sorted(unq_wave)))

        LOGGER.debug('\nBoth and Same (count):')
        both = att_curr.intersection(att_wave)
        both_same = {att for att in both if list(curr_nc['Config'].attrs[att]) == list(wave_nc['Config'].attrs[att])}
        LOGGER.debug(len(both_same))

        LOGGER.debug('\nBoth but Different:')
        both_diff = both - both_same
        LOGGER.debug(' '.join(sorted(both_diff)))

        # just printing
        LOGGER.debug('\nWhats different:')
        for att in sorted(both_diff):
            v_avg = curr_nc['Config'].attrs[att]
            v_wave = wave_nc['Config'].attrs[att]
            LOGGER.debug(f'{att}: {v_avg} != {v_wave}')

        # Transcribing Configs
        config = combo_nc.create_group('Config')
        for att in both_same:
            config.attrs[att] = curr_nc['Config'].attrs[att]
        for att in unq_curr:
            config.attrs[att] = curr_nc['Config'].attrs[att]
        for att in unq_wave:
            config.attrs[att] = wave_nc['Config'].attrs[att]
        for att in both_diff:
            config.attrs[f'{att}__WAVES'] = wave_nc['Config'].attrs[att]
            config.attrs[f'{att}__BURST'] = curr_nc['Config'].attrs[att]
        LOGGER.debug('CONFIG ATTRS: ', len(config.attrs))
        for att in config.attrs:  # convert byte-strings to strings
            try: config.attrs[att] = config.attrs[att].decode()
            except AttributeError: pass

        data = combo_nc.create_group('Data')

        # Averaged Burst/Currents Data
        LOGGER.info("Adding nc['Data']['Burst']")
        current_data = data.create_group('Burst')
        for dset_from in curr_nc['Data']['Burst'].values():
            LOGGER.debug(dset_from)
            dset_to = current_data.create_dataset(dset_from.name, data=dset_from[()])
            for att in dset_from.attrs:
                if att in ['CLASS', 'NAME', 'REFERENCE_LIST', 'DIMENSION_LIST']: continue
                dset_to.attrs[att] = dset_from.attrs[att].decode()
                if dset_to.attrs[att]: LOGGER.debug(f'    {att}: {dset_to.attrs[att]}')


        # Wave Data
        LOGGER.info("Adding nc['Data']['Waves']")
        wave_data = data.create_group('Waves')
        for dset_from in wave_nc['Data']['Waves'].values():
            LOGGER.debug(dset_from)
            dset_to = wave_data.create_dataset(dset_from.name, data=dset_from[()])
            for att in dset_from.attrs:
                if att in ['CLASS', 'NAME', 'REFERENCE_LIST', 'DIMENSION_LIST', '_FillValue']: continue
                dset_to.attrs[att] = dset_from.attrs[att].decode()
                if dset_to.attrs[att]: LOGGER.debug(f'    {att}: {dset_to.attrs[att]}')




def call_OceanContour(rawfile, param_files, timeout=60):
    # OceanContour -auto RAWFILE PARAMFILE 
    # -auto invokes the CLI
    # RAWFILE: a raw .ad2cp file to be processed
    # PARAM_FILES: processing parameter files
    
    # PARAMFILEs
    # These are generate using the "OceanContour -writeauto" command, it requires a GUI
    # For CLI use, they must include a [Section Autonomous] towards the end with the following params:
    #   File Type: (eg Burst)
    #   Export NetCDF: (eg /app/workspace/project1/ExportAuto)
    #   Project: (eg project1)
    
    # OceanContour will output processed nc files under the "{Export NetCDF}/RAWFILE" directory

    # NOTE: Even when invoked as a CLI with -auto, OceanContour still expects a windowing/GUI environment for the boot spashpage/popup
    #       To address this, we use pyvirtualdisplay "Display" to invoke a xvfb context. 
    # Despite this, OceanContour still hangs due to an error poppup on completion. For that, we use EasyProcessing's call(timeout) to recover from a hanging process.
    
    with Display(backend="xvfb") as disp:
        
        for paramfile in param_files:
            args = ['/opt/OceanContour/OceanContour', '-auto', rawfile, paramfile]
            LOGGER.info('>>', ' '.join(args))
            proc = EasyProcess(args).call(timeout=timeout)
            catlog = EasyProcess(['cat',f'{rawfile}.log']).call()
            LOGGER.info(catlog.stdout+'\n') if catlog.stdout else LOGGER.error('TASK FAILED\n')
   
    
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('rawfile')
    parser.add_argument('--params')
    parser.add_argument('--wave-params', '--wav')
    parser.add_argument('--burst-params', '--avg')
    parser.add_argument('--outfile', '-o', required=True)
    parser.add_argument('--timeout', default=40, type=int)
    parser.add_argument('--noclobber', action="store_true")
    #TODO parser.add_argument('--rawheader')
    parser.add_argument('-v', action='store_true')
    
    args = parser.parse_args()
    if args.v:
        LOGGER.setLevel(logging.DEBUG)
    
    # arg checks and combo_mode
    if args.params and any([args.wave_params, args.burst_params]):
        parser.error('When --wave-params or --burst-params are set, --params may not be set')
    if not any([args.params, args.wave_params, args.burst_params]):
        parser.error('At least on of --params, --wave-params, --burst-params must be set')
    
    COMBO_MODE = args.wave_params and args.burst_params
    if COMBO_MODE:
        assert os.path.isfile(args.wave_params)
        assert os.path.isfile(args.burst_params)
        args.wave_params = os.path.realpath(args.wave_params)
        args.burst_params = os.path.realpath(args.burst_params)
    else:
        args.params = args.wave_params or args.burst_params or args.params
        assert os.path.isfile(args.params)
        args.params = os.path.realpath(args.params)
    
    if os.path.isfile(args.outfile) and os.stat(args.outfile).st_size != 0 and args.noclobber:
        LOGGER.warning(f'NOCLOBBER: output file already exists.')
        sys.exit()

    # check filesize, skip file if it is too small, it's probably still being written to.
    assert os.path.getsize(args.rawfile)>2*1024*1024, f'Input file too small  ({ round(os.path.getsize(args.rawfile)/1024/1024) }MB). Active file?'
    # 2MB. raw adcp data file for 20 minutes is usually 5MB    
    args.rawfile = os.path.realpath(args.rawfile)
    #TODO rawfile_with_head = rawfile_checkfor_header(args.rawfile, rawheader=args.rawheader)

    os.makedirs(EXPORT_DIR, exist_ok=True)
    export_subdir = os.path.splitext(os.path.basename(args.rawfile))[0]    # AUTO  

    # Param file setup, adds/overwrites "Section Autonomous" 
    if COMBO_MODE:
        waveparams_auto = paramfile_overwrite_sectionautonomous(args.wave_params, args.wave_params.replace('.txt','.auto.txt'), PROJECT, EXPORT_DIR)
        burstparams_auto = paramfile_overwrite_sectionautonomous(args.burst_params, args.burst_params.replace('.txt','.auto.txt'), PROJECT, EXPORT_DIR)
        
        # do processing
        call_OceanContour(args.rawfile, [burstparams_auto,waveparams_auto], timeout=args.timeout)
        
        # create combo file
        wave_procfile = expected_nc_filename(waveparams_auto)
        burst_procfile = expected_nc_filename(burstparams_auto)
        wave_procfile = os.path.join(EXPORT_DIR, export_subdir, wave_procfile)
        burst_procfile = os.path.join(EXPORT_DIR, export_subdir, burst_procfile)
        assert os.path.isfile(wave_procfile)
        assert os.path.isfile(burst_procfile)
        nc_combo(wave_procfile, burst_procfile, args.outfile)
    
    else:
        params_auto = paramfile_overwrite_sectionautonomous(args.params, args.params.replace('.txt','.auto.txt'), PROJECT, EXPORT_DIR)

        # do processing
        call_OceanContour(args.rawfile, [params_auto], timeout=args.timeout)
        
        # copy output out of container
        outfile_proc = os.listdir(os.path.join(EXPORT_DIR,export_subdir))[0]
        outfile_proc = os.path.join(EXPORT_DIR, export_subdir, outfile_proc)
        shutil.copyfile(outfile_proc, args.outfile)
    

    
    
    
    
    
