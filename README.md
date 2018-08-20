# DLHub Toolbox
[![Build Status](https://travis-ci.org/DLHub-Argonne/dlhub_toolbox.svg?branch=master)](https://travis-ci.org/DLHub-Argonne/dlhub_toolbox)[![Coverage Status](https://coveralls.io/repos/github/DLHub-Argonne/dlhub_toolbox/badge.svg?branch=master)](https://coveralls.io/github/DLHub-Argonne/dlhub_toolbox?branch=master)

DLHub Toolbox contains scripts designed to make it easier to submit datasets and machine learning models to the Data and Learning Hub for Science (DLHub). This package contains tools for formatting descriptions of datasets and machine learning models in the format required by DLHub, and a wrapper around the API for sending them to DLHub for publication.

## Installation

`dlhub_toolbox` is not yet on PyPi. So, you have to install it by first cloning the repository and then calling `pip install -e .`

## Example Usage

As a simple example, we will show how to submit a machine learning model created based on the [Iris Dataset](https://archive.ics.uci.edu/ml/datasets/Iris).
Full scripts for this example model are in [/examples/iris](./examples/iris).

### Describe the Training Set

The first step is to describe the training data, which we assume is in a `csv` file named `iris.csv`. 
The `iris.csv` file looks something like

```text
# Data from: https://archive.ics.uci.edu/ml/datasets/Iris
sepal_length,sepal_width,petal_length,petal_width,species
5.1,3.5,1.4,0.2,setosa
4.9,3.0,1.4,0.2,setosa
4.7,3.2,1.3,0.2,setosa
```

To make this dataset usable for others, we want to tell them how to read it and what the columns are.
Also, to make sure the authors of the data can be properly recognized, we need to provide provenance information.
`dlhub_toolbox` provides a simple tool for specifying this information: `TabularDataset`.

```python
from dlhub_toolbox.models.datasets import TabularDataset
import pandas as pd
import json

# Read in the dataset
data = pd.read_csv('iris.csv', header=1)

# Make the dataset information
dataset_info = TabularDataset('iris.csv', read_kwargs=dict(header=1))

#   Add link to where this data was downloaded from
dataset_info.add_alternate_identifier("https://archive.ics.uci.edu/ml/datasets/Iris", "URL")

#   Add link to paper describing the dataset
dataset_info.add_related_identifier("10.1111/j.1469-1809.1936.tb02137.x", "DOI", "IsDescribedBy")

#   Mark the domain of the dataset
dataset_info.set_domain("biology")

#   Describe the columns
dataset_info.annotate_column("sepal_length", description="Length of sepal", data_type="scalar")
dataset_info.annotate_column("sepal_width", description="Width of sepal", units="cm")
dataset_info.annotate_column("petal_length", description="Length of petal", units="cm")
dataset_info.annotate_column("petal_width", description="Width of petal", units="cm")
dataset_info.annotate_column("species", description="Species", data_type='string')

#   Mark which columns are inputs and outputs
dataset_info.mark_inputs(data.columns[:-1])
dataset_info.mark_labels(data.columns[-1:])

# Describe the data provenance
dataset_info.set_title("Iris Dataset")
dataset_info.set_authors(["Marshall, R.A."])

# Print out the result
print(json.dumps(dataset_info.to_dict(), indent=2))
```

After running this script, the model produces a simple JSON description of the dataset that we will send to DLHub.

```json
{
  "datacite": {
    "creators": [
      {
        "givenName": "R.A.",
        "familyName": "Marshall",
        "affiliations": []
      }
    ],
    "titles": [
      "Iris Dataset"
    ],
    "publisher": "DLHub",
    "relatedIdentifiers": [
      {
        "relatedIdentifier": "10.1111/j.1469-1809.1936.tb02137.x",
        "relatedIdentifierType": "DOI",
        "relationType": "IsDescribedBy"
      }
    ],
    "alternateIdentifiers": [
      {
        "alternateIdentifier": "https://archive.ics.uci.edu/ml/datasets/Iris",
        "alternateIdentifierType": "URL"
      }
    ],
    "resourceType": "Dataset"
  },
  "dlhub": {
    "version": "0.1",
    "domain": "biology",
    "visible_to": [
      "public"
    ]
  },
  "dataset": {
    "path": "/home/ml_user/dlhub_toolbox/examples/iris/iris.csv",
    "format": "csv",
    "read_options": {
      "header": 1
    },
    "columns": [
      {
        "name": "sepal_length",
        "type": "scalar",
        "description": "Length of sepal"
      },
      {
        "name": "sepal_width",
        "type": "float",
        "description": "Width of sepal",
        "units": "cm"
      },
      {
        "name": "petal_length",
        "type": "float",
        "description": "Length of petal",
        "units": "cm"
      },
      {
        "name": "petal_width",
        "type": "float",
        "description": "Width of petal",
        "units": "cm"
      },
      {
        "name": "species",
        "type": "string",
        "description": "Species"
      }
    ],
    "inputs": [
      "sepal_length",
      "sepal_width",
      "petal_length",
      "petal_width"
    ],
    "labels": [
      "species"
    ]
  }
}
```

Note that the toolbox automatically put the metadata in DataCite format and includes data automatically pulled from the dataset (e.g., that the inputs are floats).

## Describe the Model

For brevity, we will upload much less metadata about a model created using Scikit-Learn.

We simply load in a Scikit-Learn model from a pickle file, and then provide a minimal amount of information about it.

```python
from dlhub_toolbox.models.servables.sklearn import ScikitLearnModel

model_info = ScikitLearnModel('model.pkl')

#    Describe the model
model_info.set_title("Example Scikit-Learn Model")
model_info.set_domain("biology")
```

The toolbox will inspect the pickle file to determine the type of the model and the version of scikit-learn that was used to create it.

```json
{
  "datacite": {
    "creators": [],
    "titles": [
      "Example Scikit-Learn Model"
    ],
    "publisher": "DLHub",
    "resourceType": "InteractiveResource"
  },
  "dlhub": {
    "version": "0.1",
    "domain": "biology",
    "visible_to": [
      "public"
    ]
  },
  "servable": {
    "type": "scikit-learn",
    "version": "0.19.1",
    "model_type": "SVC"
  }
}
```

At this point, we are ready to publish both the model and dataset on DLHub.
