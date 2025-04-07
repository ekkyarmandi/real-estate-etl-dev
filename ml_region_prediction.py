from reid.database import get_local_db, get_db as get_cloud_db
from models.listing import Listing
from decouple import config
import pandas as pd
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
from sklearn.pipeline import Pipeline
import pickle
from rich.progress import track


def data_loader():
    local_db = next(get_local_db())
    cloud_db = next(get_cloud_db())

    # load json
    data = json.load(open(config("JSON_PATH")))

    loc_data = {}
    for i in data:
        if i["Region"] != "":
            loc_data[i["Property Link"]] = {
                "region": i["Region"],
                "location": i["Location"],
                "original_value": None,
            }

    urls = list(loc_data.keys())

    listings = cloud_db.query(Listing).filter(Listing.url.in_(urls)).all()
    for listing in listings:
        loc_data[listing.url]["original_value"] = listing.location

    listings = local_db.query(Listing).filter(Listing.url.in_(urls)).all()
    for listing in listings:
        loc_data[listing.url]["original_value"] = listing.location

    return loc_data


def main():
    # Load training data
    data = pd.read_csv("location.csv")
    print(f"Training data shape: {data.shape}")

    # Load target data for prediction
    target_data = json.load(open("2025-02-01_REID_new_data_v1.json"))
    locations = {}
    for i in target_data:
        url = i["Property Link"]
        if not i["Region"] and i["Location"]:
            locations[url] = {
                "region": None,
                "location": i["Location"],
            }

    # Check if we have data to predict
    if not locations:
        print("No locations to predict.")
        return

    print(f"Found {len(locations)} locations to predict.")

    # Prepare training data
    X = data["original_value"]
    y = data["region"]

    # Split data for training and evaluation
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Create and train the model
    print("Training model...")
    model = Pipeline(
        [
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=2)),
            ("clf", RandomForestClassifier(n_estimators=100, random_state=42)),
        ]
    )

    model.fit(X_train, y_train)

    # Evaluate the model
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"Model accuracy: {accuracy:.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))

    # Save the model
    model_path = "region_prediction_model.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    print(f"Model saved to {model_path}")

    # Predict regions for target locations
    print("\nPredicting regions for target locations...")
    prediction_results = []

    for url, loc_info in locations.items():
        location_text = loc_info["location"]
        predicted_region = model.predict([location_text])[0]
        prediction_results.append(
            {
                "url": url,
                "location": location_text,
                "predicted_region": predicted_region,
            }
        )

    # Save predictions to file
    predictions_df = pd.DataFrame(prediction_results)
    predictions_df.to_csv("predicted_regions.csv", index=False)
    print(f"Predictions saved to predicted_regions.csv")

    # Print sample predictions
    print("\nSample predictions:")
    for i, pred in enumerate(prediction_results[:5]):
        print(
            f"{i+1}. Location: {pred['location']} → Region: {pred['predicted_region']}"
        )


def run_prediction_on_json():
    data = json.load(open("2025-02-01_REID_new_data_v1.json"))
    model = pickle.load(open("region_prediction_model.pkl", "rb"))
    for i in track(data, description="Predicting regions..."):
        location_text = i["Location"]
        region = i["Region"]
        if not location_text and region:
            continue
        elif not region:
            continue
        i["Region"] = model.predict([location_text])[0]
    json.dump(data, open("2025-02-01_REID_new_data_v1_predicted.json", "w"))


def run_prediction_on_cloud_db():
    cloud_db = next(get_cloud_db())
    listings = cloud_db.query(Listing).filter(Listing.location.isnot(None)).all()
    model = pickle.load(open("region_prediction_model.pkl", "rb"))
    for listing in track(listings, description="Predicting regions..."):
        location_text = listing.location
        if not location_text:
            continue
        predicted_region = model.predict([location_text])[0]
        listing.region = predicted_region
        cloud_db.commit()


if __name__ == "__main__":
    run_prediction_on_cloud_db()
