import '../data/demo_data.dart';
import '../models/patient.dart';

class PatientRepository {
  const PatientRepository();

  Future<List<Patient>> getPatients() async {
    return DemoData.patients;
  }

  Future<Patient?> getPatient(String id) async {
    for (final patient in DemoData.patients) {
      if (patient.id == id) return patient;
    }
    return null;
  }
}
