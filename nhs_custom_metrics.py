# -*- cod"ing: utf-8 -*-
'''

@author:    Liam Stubbington, 
            RT Physicist, Cambridge University Hospitals NHS Foundation Trust

'''

from proknow import ProKnow, Exceptions 
from progress.bar import ChargingBar
from datetime import datetime 
from csv import DictReader, DictWriter
from json import dump 
from itertools import chain
from exceptions.nhs_exceptions import *
from log.nhs_proknow_log import NHSProKnowLog
import os, errno

class NHSProKnow(): 
    ''' 
    Script object for interfacing with ProKnow. 
    Subsequent object templates may inherit this. 

    '''
    def __init__(
        self, proknow_url: str = "https://nhs.proknow.com",
        API_KEY: str = None, workspace: str = None,
        ):

        try:
            self.pk = ProKnow(base_url = proknow_url, 
            credentials_file = API_KEY)
        except:
            raise NoAPIKey()

        self.ws = workspace

class NHSCustomMetric(): 
    '''
    Script object for adding/checking existence of CMs in ProKnow organisation.

    Attributes: 
        custom_metric 
            dict, with the following keys:
                PatientID, CustomMetricName, Value, Context, Description 
        pk
            proknow object for interfacing with ProKnow 
        check_result
            str, error_message for logging 
        create_result
            str, as above 
    
    Methods: 
        convert_context 
            ProKnow is very particular about the context field. 
            "context" must be one of
                patient, study, image_set, structure_set, plan, dose
        check_cm
        create_cm
            Tries to parse Value as a float. 
            If successful, CM is added as type numbers, otherwise string. 

    '''

    def __init__(self, custom_metric: dict, proknow) -> str:
        self.pk = proknow
        self.custom_metric = self.convert_context(custom_metric)
        self.check_result = self.check_cm()
        if "exists in ProKnow" not in self.check_result:
            self.create_result = self.create_cm()
        else:
            self.create_result = (
                f"{self.custom_metric['CustomMetricName']} "
                "not created."
            )
    
    def convert_context(self, custom_metric) -> dict:
        context = custom_metric['Context'].strip().lower().replace(" ","_")
        custom_metric['Context'] = context
        return custom_metric

    def check_cm(self) -> str:
        try: 
            self.pk.custom_metrics.resolve(
                self.custom_metric["CustomMetricName"]
            )
            return (f"{self.custom_metric['CustomMetricName']} exists in ProKnow.")
        except: 
            return (f"Could not resolve {self.custom_metric['CustomMetricName']}"
                    " by Name, attempt to create a new CM."
            )

    def create_cm(self) -> str:
        try:
            float(self.custom_metric['Value'])        
            self.pk.custom_metrics.create(
                name = self.custom_metric['CustomMetricName'], 
                context = self.custom_metric["Context"],
                type = {
                    "number": {}
                }
                )
            return(
                f"Custom Metric: {self.custom_metric['CustomMetricName']} "
                "will be added as type Numbers."
            )
        except ValueError: 
            self.pk.custom_metrics.create(
                name = self.custom_metric['CustomMetricName'],
                context = self.custom_metric["Context"],
                type = {
                    "string": {}
                }
            )
            return(
                f"Custom Metric: {self.custom_metric['CustomMetricName']} will be added "
                " as type Text."
            )
            

class NHSCustomMetricsFromCSV(NHSProKnow):
    '''
    Script object template for adding Custom Metric values to patient entities, 
    matching on the Description field, from CSV.  
    
    Attributes: 
        csv
            list of dicts.
            Must have: 
                PatientID, CustomMetricName, Description, Context, Value
        log_lines
            list of strs.
            For logging. 
        
    Methods:
        add_cms_from_csv
            Only contexts of patient, image_set, structure_set, dose, plan
            are supported. 
            Finds entities with exactly matching type and description. 
        write_logs

    '''
    def __init__(self, csv_path: str = "./custom_metrics.csv", **kwargs):
        super().__init__(**kwargs)

        try:
            with open(os.path.normpath(csv_path), 'r', encoding="utf-8") as f:
                self.csv = list(DictReader(f, delimiter = ","))
        except:
            raise FileNotFoundError(
                errno.ENOENT, os.strerror(errno.ENOENT),
                os.path.normpath(csv_path)
            )

        self.log_lines = []

    def write_logs(self, log_path = None):
        logger = NHSProKnowLog(
            log_path = log_path,
            log_lines = self.log_lines
        )

    def _update_meta(self, entity, cm: dict):
        '''
        Update entity metadata. 
        '''
        meta = entity.get_metadata()
        if "string" in self.pk.custom_metrics.resolve(cm["CustomMetricName"]).type:
            meta[cm["CustomMetricName"]] = cm["Value"]
        else:
            meta[cm["CustomMetricName"]] = float(cm["Value"])
        entity.set_metadata(meta)
        entity.save()


    def add_cms_from_csv(self):

        self._cms = [
            NHSCustomMetric(cm, self.pk) for cm in self.csv
        ]

        print("Adding Custom Metric values to entities from csv...")
        with ChargingBar('Processing CMs: ', max = len(self._cms)) as bar:
            for nhs_cm in self._cms: 

                self.log_lines.append(
                    nhs_cm.check_result
                )

                self.log_lines.append(
                    nhs_cm.create_result
                )

                cm = nhs_cm.custom_metric

                patients = self.pk.patients.lookup(
                    self.ws, [cm['PatientID']]
                    )

                if len(patients) > 1:
                    # raise PatientIDNotUniqueError(cm['PatientID'])
                    self.log_lines.append(
                        f"ERROR! \n PatientID: {cm['PatientID']} not unique. \n"
                        f"No further processing on {cm['CustomMetricName']}"
                    )

                else:
                    patient = patients[0].get()

                    if cm["Context"] == "patient":
                        self._update_meta(
                            patient, 
                            cm
                        )
                        self.log_lines.append(
                                f"SUCCESS! {cm['PatientID']} \n"
                                f"{cm['CustomMetricName']} with value: {cm['Value']} added."
                            )

                    else:
                        entities = patient.find_entities(
                            type=cm["Context"],
                            description = cm['Description']
                        )

                        if not entities: 
                            # raise EntityNotFoundError
                            self.log_lines.append(
                                f"ERROR! {cm['PatientID']} \n"
                                f"No {cm['Context']} with description: {cm['Description']}"
                            )

                        elif len(entities) > 1:
                            self.log_lines.append(
                                f"ERROR! {cm['PatientID']} \n"
                                f"{cm['Context']} with description: {cm['Description']} "
                                "is not unique!"
                            )

                        else: 
                            ent = entities[0].get()     
                            self._update_meta(
                                ent,
                                cm
                            )
                            self.log_lines.append(
                                f"SUCCESS! {cm['PatientID']} \n"
                                f"{cm['CustomMetricName']} with value: {cm['Value']} added."
                            )
                self.log_lines.append(
                    " ----------------------------------------------------------------------- "
                )
                bar.next()
        print("Done!")
        self.write_logs() 

class NHSCustomMetricsFromDICOM(NHSProKnow):
    '''
    Script object template for adding DICOM attributes as Custom Metrics 
    across a ProKnow Workspace collection. 

    Note: DICOM is misleading, all of the values added are available from
    the ProKnow UI. 

    Attributes:
        • collection: str
        • collection_patients: list 
        • log_lines: list of dicts 

    Methods: 
        • write_all_custom_metrics
    '''
    def __init__(self, collection: str = 'My Collection', **kwargs):
        super().__init__(**kwargs)
        self.collection = collection 

        collection_item = self.pk.collections.find(workspace = self.ws, name=self.collection).get()
        self.collection_patients = collection_item.patients.query()

        # TO-DO read this from file 
        self.nhs_custom_metrics = [
            ("*NHS - TPS Vendor", "VARIAN", "plan"),
            ("*NHS - TPS", "Eclipse v.x", "plan"),
            ("*NHS - TDS S/N", "sn2079", "plan"),
            ("*NHS - #Fractions", 20, "plan"),
            ("*NHS - Modality", "Electrons", "plan"),
            ("*NHS - Fluence Mode", "FFF", "plan"),
            ("*NHS - MeanBeamEnergy",6 , "plan"),
            ("*NHS - Prescriptions [Gy]", "60/48", "plan"),
            ("*NHS - Approx. age at imaging [years]", 52, "image_set")
            
        ]

        for thing in self.nhs_custom_metrics:
            dict_cm = {
                'CustomMetricName': thing[0],
                'Value': thing[1],
                'Context': thing[2]
            }
            NHSCustomMetric(dict_cm, self.pk)

    def write_all_custom_metrics(self):

        print(
            "Writing *NHSCustomMetrics for patients in "
            f"{self.collection}."
            )

        with ChargingBar('Processing Patients: ', 
        max=len(self.collection_patients)) as bar:
            for patient in self.collection_patients:
                px = self.pk.patients.find(workspace = self.ws, id=patient.id).get()
                if px.birth_date:
                    dob = datetime.strptime(px.birth_date, '%Y-%m-%d') 
                else:
                    dob = None

                # TO-DO 
                    # logs 
                    # leap years - Age at imaging?
                    # dose?

                # IMAGE SETS 
                if dob:
                    for image_entity in px.find_entities(type="image_set"):
                        entity = image_entity.get()
                        if entity.data['series']['date']: 
                            series_date = datetime.strptime(
                                entity.data['series']['date'],
                                '%Y-%m-%d'
                            )
                            image_age = (series_date - dob).days//364.2425
                            meta = {
                                    "*NHS - Approx. age at imaging [years]": image_age
                            }
                            meta = {**entity.get_metadata(), **meta}
                            entity.set_metadata(meta)
                            entity.save()

                # PLANS
                for plan_entity in px.find_entities(type="plan"):
                    entity = plan_entity.get()
                    del_info = entity.get_delivery_information()

                    equipment = del_info['equipment'] 

                    total_fractions = sum(
                        [fg['number_of_fractions_planned'] for fg in del_info['fraction_groups']]
                    ) 
                    beams = del_info['beams']

                    technique = " ".join( item for item  in {
                        " ".join([
                            beam['delivery_modality'],
                            beam['radiation_type'],
                            beam['delivery_modality'],
                            f"IMRT: {beam['is_modulated']}",
                            f"Helical: {beam['is_helical']}",
                            ])
                        for beam in beams
                    })

                    try:
                        prescriptions ="/".join([rx['prescribed_dose'] for rx in
                        entity.data['prescription']['dose_references'] ])
                    except KeyError:
                        prescriptions = "FAILURE"

                    if equipment['device_serial_number']:
                        sn = equipment['device_serial_number']
                    else:
                        sn = "No TDS S/N specified in plan."

                    try:
                        fluence_mode = " ".join([ item for item  in {
                            beam['primary_fluence_mode']['mode'] for beam in beams
                        }])
                    except TypeError:
                        fluence_mode = "FAILURE"

                    nominal_beam_energies = list(chain(*[
                        beam['control_point_summary']['nominal_beam_energies'] 
                        for beam in beams
                    ])) 
                    mean_beam_energy = sum(nominal_beam_energies)/len(nominal_beam_energies)

                    meta = {
                        "*NHS - TPS Vendor": equipment['manufacturer'],
                        "*NHS - TPS": equipment['manufacturer_model_name'], 
                        "*NHS - TDS S/N": sn, 
                        "*NHS - #Fractions": total_fractions,
                        "*NHS - Modality": technique,
                        "*NHS - Fluence Mode": fluence_mode,
                        "*NHS - MeanBeamEnergy": mean_beam_energy,
                        "*NHS - Prescriptions [Gy]": prescriptions
                    }

                    meta = {**entity.get_metadata(), **meta}
                    entity.set_metadata(meta)
                    entity.save()
                
                bar.next()
        print("Done!")

    
    
class NHSGetEntityDescriptions(NHSProKnow): 
    '''
    Script object template for getting a csv file of all entities 
    for patients in a collection.  

    Attributes:
        • collection: str
        • collection_patients: list 
            PatientSummary items in the collection 

    Methods: 
        • write_all_entities_to_csv
        • get_all_entities_for_patient
            returns a dict of summary data for all entities 
            belonging to a patient in a collection 
    '''
    def __init__(self, collection: str = 'My Collection', **kwargs):
        super().__init__(**kwargs)
        self.collection = collection 

        collection_item = self.pk.collections.find(workspace = self.ws, name=self.collection).get()
        self.collection_patients = collection_item.patients.query()

    def get_all_entities_for_patient(self, patient, compare_id:str = None) -> list:
        '''
            Params: 
                patient: ProKnow patient object. 
                compare_id: str 

            Returns:
                list of dicts
                each dict has the following kwargs: 
                    PatientID, Type, Description, InCollection?
                        Type: dose, plan, image_set, structure_set 
                        Description: entity description 
                        InCollection?: true if entity is in the collection 
        '''

        contexts = [
            "plan", "dose","image_set","structure_set"
        ]

        # TO-DO list comprehension 
        data = []
        for context in contexts: 
            for entity_summary in patient.find_entities(type=context):
                entity = entity_summary.get() 
                data.append({
                    "PatientID" : patient.mrn,
                    "Context": context, 
                    "Description": entity.description,
                    "InCollection?": entity.id == compare_id
                })
        return data

    def write_all_entities_to_csv(self, csv_out:str = None):
        '''
            Params: 
                csv_out: str (optional)
                    output CSV file 
        '''
        if not csv_out:
            csv_out =  self.collection + "_patient_entities.csv"

        # TO-DO list comprehension 
        data = []
        print(f"Getting entities for patients in collection {self.collection}.")
        with ChargingBar(
            'Processing Patients: ', max = len(self.collection_patients)
            ) as bar:
            for patient in self.collection_patients:
                entity_in_collection_id = patient.data['entity']['id']
                px = self.pk.patients.find(workspace = self.ws, id=patient.id).get()
                for item in self.get_all_entities_for_patient(px, entity_in_collection_id):
                    data.append(item)
                bar.next()

        with open(csv_out, 'w', encoding="utf-8", newline="") as f: 
            dict_writer = DictWriter(f, data[0].keys())
            dict_writer.writeheader()
            dict_writer.writerows(data)
        
        print("Done!")


class NHSJSONProKnowEntity(NHSProKnow):
    '''
    Script object template for dumping a ProKnow entity object to JSON. 

    ProKnow entity objects have a read-only property called data - which should 
    be JSON serializable. 

    One of either a ProKnow entity object can be specified or a unique 
    patient MRN - in which case, *all ProKnow entities for that particular patient
    will be written to JSON. 

    *Entities of type Study are not supported. 

    Params:
        • patient 
            ProKnow patient object. 
        • entity (optional)
        • f_root (optional)
            target path for output JSON data. 

    Methods:
        • write_json_entity
            - entity 
        • write_json_plan_delivery_info
            - plan_entity
        


    '''
    def __init__(self, patient_mrn, entity = None, f_root: str = None, **kwargs):
        super().__init__(**kwargs)

        if not (patient_mrn or entity):
            raise ValueError

        if not f_root:
            self.f_root = "."
        else:
            self.f_root = f_root 

        if entity:
            self.write_entity(entity)

        elif patient_mrn:
            patients = self.pk.patients.lookup(self.ws, [patient_mrn])

            if len(patients) > 1:
                raise PatientIDNotUniqueError(patient_mrn)
            else:
                patient = patients[0].get()

            entities = [
                patient.find_entities(type="plan"),
                patient.find_entities(type="dose"),
                patient.find_entities(type="image_set"),
                patient.find_entities(type="structure_set"),
            ]

            for plan_entity in entities[0]:
                self.write_json_plan_delivery_info(plan_entity.get())

            for entity in chain(*entities):
                self.write_entity(entity.get())

            try:
                f_name = patient_mrn + '.json'
                with open(os.path.normpath(os.path.join(f_root, f_name)),
                "w",encoding = "utf-8") as f:
                    dump(patient.data, f, indent=4)
            except:
                print(f"FAIL: {patient.mrn}")

    def write_entity(self, entity):
        f_name = entity.data['type'] +"_"+ entity.id +'.json'
        try:
            with open(os.path.normpath(os.path.join(self.f_root, f_name)),"w",
                    encoding = "utf-8") as f:
                    dump(entity.data, f, indent=4)
        except: 
            print(f"FAILURE: {entity.description} of type: "
            f"{entity.data['type']}")
    
    def write_json_plan_delivery_info(self, plan_entity):
        f_name = "plan_delivery_info_"+plan_entity.id+'.json'
        try:
            with open(os.path.normpath(os.path.join(self.f_root, f_name)),"w",
                    encoding = "utf-8") as f:
                    dump(plan_entity.get_delivery_information(), f, indent=4)
        except Exceptions.HttpError : 
            print(f"FAILURE: {plan_entity.description} get_delivery_info().")
