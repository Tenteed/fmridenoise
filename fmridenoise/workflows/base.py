from nipype.pipeline import engine as pe
from niworkflows.interfaces.bids import DerivativesDataSink

from fmridenoise.interfaces.loading_bids import BIDSSelect, BIDSLoad
from fmridenoise.interfaces.confounds import Confounds
from fmridenoise.interfaces.denoising import Denoise
from fmridenoise.interfaces.pipeline_selector import PipelineSelector
from nipype.interfaces import fsl, utility as niu, io as nio


import fmridenoise
import os
import glob

# from nipype import config
# config.enable_debug_mode()


#DATA_ITEMS = ['bold', 'regressors']

#class DerivativesDataSink(BIDSDerivatives):
#    out_path_base = 'fmridenoise'


def init_fmridenoise_wf(bids_dir,
                        output_dir,
                        derivatives=True,
                        pipelines_paths=glob.glob(os.path.dirname(fmridenoise.__file__) + "/pipelines/*"),
                        #, desc=None,
                        # ignore=None, force_index=None,
                        # model=None, participants=None,
                        base_dir=None, name='fmridenoise_wf'
                        ):

    wf = pe.Workflow(name='fmridenoise', base_dir=None)

    # datasource = pe.Node(niu.Function(function=_dict_ds, output_names=DATA_ITEMS),
    #                      name='datasource')
    # datasource.inputs.in_dict = in_files
    # datasource.iterables = ('sub', sorted(in_files.keys()))

    # 1) --- Selecting pipeline

    # Inputs: fulfilled
    pipelineselector = pe.Node(
       PipelineSelector(),
       name="PipelineSelector")
    pipelineselector.iterables = ('pipeline_path', pipelines_paths)
    # Outputs: pipeline

    # --- Tests

    # reader = pe.Node(PipelineSelector(), name="pipeline_selector") # --- this is temporary solution
    # for path in glob.glob("../pipelines/*"):
    #     path = os.path.abspath(path)
    #     reader.inputs.pipeline_path = path
    #     pipeline = reader.run()

    # 2) --- Loading BIDS structure

    # Inputs: directory
    loading_bids = pe.Node(
        BIDSLoad(
            bids_dir=bids_dir, derivatives=derivatives
        ),
        name="BidsLoader")
    # Outputs: entities

    # 3) --- Selecting BIDS files

    # Inputs: entities
    selecting_bids = pe.MapNode(
        BIDSSelect(
            bids_dir=bids_dir,
            derivatives=derivatives
        ),
        iterfield=['entities'],
        name='BidsSelector')
    # Outputs: fmri_prep, conf_raw, entities

    # 4) --- Confounds preprocessing

    # Inputs: pipeline, conf_raw
    prep_conf = pe.MapNode(
        Confounds(#pipeline=pipeline.outputs.pipeline,
                  output_dir=output_dir,
                  ),
        iterfield=['conf_raw'],
        name="ConfPrep")
    # Outputs: conf_prep

    # 5) --- Denoising

    # Inputs: conf_prep
    denoise = pe.MapNode(
        Denoise(output_dir=output_dir,
                ),
        iterfield=['fmri_prep', 'conf_prep'],
        name="Denoise")
    # Outputs: fmri_denoised

    # 6) --- Save derivatives

    # Inputs: conf_prep
    ds_confounds = pe.Node(
        DerivativesDataSink(
            base_directory=str(output_dir),
            keep_dtype=False,
            suffix='prep'
        ),
        #iterfield=['conf_prep'],
        name='conf_prep',
        run_without_submitting=True)

# --- Connecting nodes

    wf.connect([
        (loading_bids, selecting_bids, [('entities', 'entities')]),
        (selecting_bids, prep_conf, [('conf_raw', 'conf_raw')]),
        #(prep_conf, ds_confounds, [('conf_source', 'source_file')]),
        (pipelineselector, prep_conf, [('pipeline', 'pipeline')]),
        (selecting_bids, denoise, [('fmri_prep', 'fmri_prep')]),
        (prep_conf, denoise, [('conf_prep', 'conf_prep')]),
        #(prep_conf, ds_confounds, [('conf_prep', 'in_file')]),  # --- still not working with this line
    ])

    return wf


#def _dict_ds(in_dict, sub, order=['bold', 'regressors']):
#    return tuple([in_dict[sub][k] for k in order])


# --- TESTING

if __name__ == '__main__':
    bids_dir = '/home/finc/Dropbox/Projects/fitlins/BIDS/'
    output_dir = '/media/finc/Elements/fmridenoise/derivatives/fmridenoise/'
    wf = init_fmridenoise_wf(bids_dir,
                             output_dir,
                             derivatives=True)
    wf.run()
    wf.write_graph("workflow_graph.dot")