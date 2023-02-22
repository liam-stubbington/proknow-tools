class NoAPIKey(Exception):
    ''' 
        Exception raised when no API key is provided. 

        Attributes:
            • error_message 

    '''

    def __init__(self):
        self.error_message = "No API key provided."
        super().__init__(self.error_message)


class PatientIDNotUniqueError(Exception):
    '''
        Exception raised when more than one patient found when filtering by 
        MRN. 

        Attributes: 
            • mrn
            • error_message
                - PatientID: {mrn} not unique! 
    '''
    def __init__(self, mrn):
        self.mrn = mrn 
        self.error_message = f"PatientID: {self.mrn} not unique!"
        super().__init__(self.error_message)

class EntityNotFoundError(Exception):
    ''' 
        Exception raised when entity label does not exist in ProKnow.

        Attributes:
            • entity_label
            • error_message

    '''
    def __init__(self, entity_label):
        self.entity_label = entity_label 
        self.error_message = (
            f"The object with label: {self.entity_label} "
            "could not be found in ProKnow!"
            )
        super().__init__(self.error_message)

