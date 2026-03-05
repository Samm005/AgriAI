import joblib
import pickle

model = pickle.load(open("model.pkl","rb"))
joblib.dump(model,"model.joblib",compress=3)

model2 = pickle.load(open("severity_model.pkl","rb"))
joblib.dump(model2,"severity_model.joblib",compress=3)