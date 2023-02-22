## NHS Custom Metrics - ProKnow Helper Classes
This project contains a set of script object templates that extend the core capabilities of the ProKnow API's handling of Custom Metrics. 

**IPEM PTOG Custom Metrics** <br>
Author: Liam Stubbington, RT Physicist 
<br>Cambridge University Hospitals NHS Foundation Trust 

---
## Quick Start 

Follow the [ProKnow docs](https://proknow-python.readthedocs.io/en/latest/usage.html#installation) to setup your environment if you have not done so already. 

We need to start by setting up the ProKnow API:

```
    kwargs = {
        "proknow_url": "https://nhs.proknow.com",
        "API_KEY": "./api/credentials.json",
        "workspace" : "RGT - Cambridge University Hospitals"
    }
```

This is forwarded on to the rest of our objects. 

We also need to import our objects. 

```
    from nhs_custom_metrics import *
```

### Adding Custom Metrics From DICOM 
```
    my_thing = NHSCustomMetricsFromDICOM(
    collection = 'Breast-Left',
    **kwargs,
    )

    my_thing.write_all_custom_metrics()
```
This will add the following CMs across all entities for all patients listed in the collection 'Breast-Left'. 

1. *NHS - TPS Vendor, plan
2. *NHS - TPS, plan
3. *NHS - TDS S/N, plan
4. *NHS - #Fractions, plan
5. *NHS - Modality, plan
6. *NHS - Fluence Mode, plan
7. *NHS - MeanBeamEnergy, plan
8. *NHS - Prescriptions (Gy), plan
9. *NHS - Approx. age at imaging (years), image_set

Approximate age at imaging is due to dividing the difference in days by 365.24.

MeanBeamEnergy is better for scanned proton beams which have a spread in energies.

### Getting a CSV file of all entity descriptions in a collection 

This is really useful if we wish to add CM values to specific entities. We use the description field to match. 

The following will get all entity descriptions for all patients in the workspace collection 'Lung SABR'. 

```
    my_thing = NHSGetEntityDescriptions(
        collection = 'Lung SABR',
        **kwargs
    )

    my_thing.write_all_entities_to_csv(
        csv_out = "./custom_metrics/entity_descriptions.csv"
    )
```

The output csv file looks something like this:

![Entity descriptions CSV file.](/screenshots/entity_descriptions.PNG)

### Importing Custom Metrics Values from CSV

Following on from the above, we want to assign custom metric values to specific entities. To do this, we use a modified copy of the CSV file produced in the [above](#getting-a-csv-file-of-all-entity-descriptions-in-a-collection). 

```
    my_thing = NHSCustomMetricsFromCSV(
        csv_path = "./custom_metrics/custom_metrics.csv"
    )

    my_thing.add_cms_from_csv()
```

The CSV needs to have the following column headings
- PatientID
- CustomMetricName
- Value
- Description 
- Context 

If the CustomMetricName does not exist in ProKnow, it will be added for you based on the Value. The Description should match an entity description, and the context is one of plan, dose, patient, image_set, structure_set.

For example:

![Example entity custom metrics csv file.](/screenshots/custom_metrics_csv.PNG).

---
## Reference Guide  
Notes on the individual script objects. 

### NHSProKnow
Script object for interfacing with ProKnow. 
Mainly use is as a parent object for subsequent classes. 

Initialisation:
```
    nhs_pk = NHSProKnow(
        proknow_url = "https://nhs.proknow.com",
        API_KEY = "path_to_credentials.json",
        workspace = "ProKnow Workspace Label" 
    )
```
API_KEY should have the necessary permissions for the Workspace. 

### NHSCustomMetric
Script object for adding/checking existence of CMs in ProKnow organisation.  

Attributes: 
- custom_metric 
    - dict, with the following keys:
        PatientID, CustomMetricName, Value, Context, Description 
- pk
    - proknow object for interfacing with ProKnow 
- check_result
    - str, error_message for logging 
- create_result
    - str, as above 

Methods: 
- convert_context 
    - goes some way to ensuring if Context is valid 
    - ProKnow is very particular about the context field. 
        - "context" must be one of: patient, study, image_set, structure_set, plan, dose
- check_cm
    - Checks if CM exists in organisation. 
    - Returns: str, error message
- create_cm
    - Creates a CM in organisation 
    - Tries to parse Value as a float. If successful, CM is added as type numbers, otherwise string. 
    - Returns: str, error message

### NHSCustomMetricsFromCSV
Script object for adding CMs values to patient entities, matching on the Description field, from CSV.  

Initialisation parameters:
- csv_path 
    - path to csv file: str
    
Attributes: 
- csv
    - list of dicts. Each dict must have: PatientID, CustomMetricName, Description, Context, Value
- log_lines
    - list of strs for logging. 
        
Methods:
- add_cms_from_csv
    - Contexts of patient, image_set, structure_set, dose, plan are supported
    - Finds entities with exactly matching type and description. 
- write_logs(log_path)
    - log_path: str 
        - path to logging directory 
    - writes the log file: str

See [quick start](#quick-start) for usage. 

### NHSCustomMetricsFromDICOM
Script object for adding DICOM attributes as Custom Metrics across a ProKnow Workspace collection. 

DICOM is misleading, all of the values added are available from the ProKnow UI. 

Attributes:
- collection: str
- collection_patients: list 
- log_lines: list of dicts 

Methods: 
- write_all_custom_metrics

See [quick start](#quick-start) for usage. 

### NHSGetEntityDescriptions
Script object template for getting a csv file of all entities for patients in a collection. This is great when used in combined with a [NHSCustomMetricsFromCSV](#nhscustommetricsfromcsv) object. 

Attributes:
- collection: str
- collection_patients: list 
    - PatientSummary items in the collection 

Methods: 
- write_all_entities_to_csv
    - params:
        - csv_out: str (optional) 
    - output csv has the following column headings:
        - PatientID, Type, Description, InCollection?,
        - InCollection? is True if the entity is in the collection 

See [quick start](#quick-start) for usage. 

### NHSJSONProKnowEntity
It is sometimes helpful to dump an entity to json for inspection. 

Initialisation options:

1. patient_mrn: str, if a patient_mrn is provided, all entities belonging to that patient are dumped to json. 
2. entity: ProKnow Entity object, a single entity is dumped to json. 

f_path should be provided and is a path to the output json data directory.  

Example usage: 

```
    px = "RGQXYZ"

    my_json_thing = NHSJSONProKnowEntity(
        patient_mrn = px,
        f_root = "./custom_metrics/",
        **kwargs
    )

```

---

## Logging

### NHSProKnowLog
Writes a list of strings, or a list of dicts to a log file. 
The default filename and path contains the time of instantiation. 

Attributes:
- log_lines: list 
    - list of strings or list of dicts
- log_path: str 
    - path to log directory 
- headers: str (optional)
    - list of column headings for writing list of dictionaries  

Methods:
- write_list_of_strs 
- write_list_of_dicts 

Example usage:
```
log_lines = [
    {
        "Keyword1": 1,
        "Keyword2": 2, 
    },
    {
        "Keyword1":"one",
        "Keyword2":"two",
    }
]

my_logger = NHSProKnowLog(
            log_path = "./some_path_to_the_log_file",
            log_lines = self.log_lines
            headers = log_lines.keys()
        )
```

---
## Exceptions

### NoAPIKey
Exception raised when no API key is provided. 

Attributes:
 - error_message 

### PatientIDNotUniqueError
Exception raised when more than one patient found when filtering by MRN. 

Attributes: 
- mrn
- error_message

### EntityNotFoundError

Exception raised when entity label does not exist in ProKnow.

Attributes:
    - entity_label
    - error_message

---
### Notes 
Context:  [patient, study, image_set, structure_set, plan, dose]
Types: [number, string, enum]

Study and Patient are the difficult ones. 
patient_item.studies returns a list of StudySummary items. 
Everything is read-only - do Studies have metadata? 