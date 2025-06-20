#! /bin/bash
#
# Run script for flywheel/mri-synthseg Gear.
#
# Authorship: Niall bourke
#
# NOTE: Need to disable Rosetta to debug on M1 Macs
##############################################################################
# Define directory names and containers

FLYWHEEL_BASE=/flywheel/v0
INPUT_DIR=$FLYWHEEL_BASE/input/
OUTPUT_DIR=$FLYWHEEL_BASE/output
CONFIG_FILE=$FLYWHEEL_BASE/config.json
CONTAINER='[flywheel/mri-synthseg]'

source /usr/local/freesurfer/SetUpFreeSurfer.sh
##############################################################################
# Parse configuration
function parse_config {

  CONFIG_FILE=$FLYWHEEL_BASE/config.json
  MANIFEST_FILE=$FLYWHEEL_BASE/manifest.json

  if [[ -f $CONFIG_FILE ]]; then
    echo "$(cat $CONFIG_FILE | jq -r '.config.'$1)"
  else
    CONFIG_FILE=$MANIFEST_FILE
    echo "$(cat $MANIFEST_FILE | jq -r '.config.'$1'.default')"
  fi
}

# define output choise:
config_output_nifti="$(parse_config 'output_nifti')"
config_output_mgh="$(parse_config 'output_mgh')"
# define options:
config_parc="$(parse_config 'parc')"
config_vol="$(parse_config 'vol')"
config_qc="$(parse_config 'QC')"
config_rob="$(parse_config 'robust')"

echo "Parcelation is ${config_parc}"
echo "Save volume output is $config_vol"
echo "Save QC output is $config_qc"
##############################################################################
# Define brain and face templates

brain_template=$FLYWHEEL_BASE/talairach_mixed_with_skull.gca
face_template=$FLYWHEEL_BASE/face.gca

##############################################################################
# Handle INPUT file

# Find input file In input directory with the extension
# .nii, .nii.gz
input_file=`find $INPUT_DIR -iname '*.nii' -o -iname '*.nii.gz'`

# Check that input file exists
if [[ -e $input_file ]]; then
  echo "${CONTAINER}  Input file found: ${input_file}"

    # Determine the type of the input file
  if [[ "$input_file" == *.nii ]]; then
    type=".nii"
  elif [[ "$input_file" == *.nii.gz ]]; then
    type=".nii.gz"
  fi
  # Get the base filename
  base_filename=`basename "$input_file" $type`
  
else
  echo "${CONTAINER} inputs were found within input directory $INPUT_DIR"
  exit 1
fi

##############################################################################
# Run mri_synthseg algorithm

# Set initial exit status
mri_synthseg_exit_status=0

# Set base output_file name
output_file=$OUTPUT_DIR/"$base_filename"'_synthseg'
echo "output_file is $output_file"

# Check if user wanted parcelation output
if [[ $config_parc == 'true' ]]; then
  parc='--parc'
fi
if [[ $config_vol == 'true' ]]; then
  vol=`echo --vol $OUTPUT_DIR/vol.csv`
fi
if [[ $config_qc == 'true' ]]; then
  qc=`echo --qc $OUTPUT_DIR/qc.csv`
fi
if [[ $config_rob == 'true' ]]; then
  robust='--robust'
fi

# Run synthseg with options
if [[ -e $input_file ]]; then
  echo "Running synthseg..."
  mri_synthseg --i $input_file --o $OUTPUT_DIR $parc $vol $qc $robust
  mri_synthseg_exit_status=$?
fi

##############################################################################
# Handle Exit status

if [[ $mri_synthseg_exit_status == 0 ]]; then
  echo -e "${CONTAINER} Success!"
  exit 0
else
  echo "${CONTAINER}  Something went wrong! mri_synthseg exited non-zero!"
  exit 1
fi
# return [mri_synthseg_exit_status]
