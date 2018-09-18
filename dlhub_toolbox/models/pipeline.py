"""Model for a pipeline of several servables"""
from dlhub_toolbox.models import BaseMetadataModel


class PipelineModel(BaseMetadataModel):
    """Model for a pipeline of several servables

    A Pipeline is created after individual servables have been published in DLHub, or at least
    assigned a DLHub identifier. A Pipeline is formed from a list of these servables, and any
    options to employ when running them. A step in a pipeline could also be another pipeline.

    A simple example for a DLHub pipeline is an image classification tool. The first step in the
    pipeline is an image reader take takes any image type and produces an array. The second step
    standardizes the shape of the image, where the "options" to the servable are the desired
    resolution and whether the image is grayscale or not. The final step is the classification
    pipeline. Put together, the image pipeline can support any type of input data.
    """

    def __init__(self):
        super(PipelineModel, self).__init__()
        self.steps = []

    def add_step(self, identifier, description, parameters=None):
        """Add a step to the pipeline

        Args:
            identifier (string/BaseMetadataModel): The DLHub identifier of the step (a UUID)
            description (string): A short description of this step
            parameters (dict): Any options for the servable. See the list of parameters for a servable
        """

        # Get the identifier if the user provides a metadata model, rather than a string
        if isinstance(identifier, BaseMetadataModel):
            identifier = identifier.dlhub_id

        # Compose the block
        step = {
            'dlhub_id': identifier,
            'description': description,
        }
        if parameters is not None:
            step['parameters'] = parameters
        self.steps.append(step)

    def to_dict(self, simplify_paths=False):
        output = super(PipelineModel, self).to_dict(simplify_paths)

        # Make as a "InteractiveResource"
        output['datacite']['resourceType'] = {'resourceTypeGeneral': 'InteractiveResource'}

        # Add the pipeline information
        output['pipeline'] = {'steps': self.steps}
        return output
