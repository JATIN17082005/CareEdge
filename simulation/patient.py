class Patient:
    def __init__(
        self,
        patient_id="P001",
        heart_rate=75,
        spo2=98,
        temperature=36.8,
        systolic_bp=120,
        diastolic_bp=80,
    ):
        self.patient_id = patient_id
        self.heart_rate = heart_rate
        self.spo2 = spo2
        self.temperature = temperature
        self.systolic_bp = systolic_bp
        self.diastolic_bp = diastolic_bp

    def get_baseline(self):
        return {
            "patient_id": self.patient_id,
            "heart_rate": self.heart_rate,
            "spo2": self.spo2,
            "temperature": self.temperature,
            "systolic_bp": self.systolic_bp,
            "diastolic_bp": self.diastolic_bp,
        }