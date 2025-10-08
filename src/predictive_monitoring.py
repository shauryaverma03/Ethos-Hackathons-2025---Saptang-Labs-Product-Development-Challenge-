from sklearn.ensemble import RandomForestClassifier
import pickle

def train_predictor(X, y):
    clf = RandomForestClassifier()
    clf.fit(X, y)
    with open('../models/predictive_model.pkl', 'wb') as f:
        pickle.dump(clf, f)
    return clf

def predict_state(model, features):
    return model.predict([features])
