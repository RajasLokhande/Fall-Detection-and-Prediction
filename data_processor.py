import numpy as np
import pandas as pd
import glob
import os
import random
from tqdm import tqdm


class DatasetProcessor:
    def get_file_name(self, path, ratio=0.8):
        path = os.path.normpath(path)
        search_pattern = os.path.join(path, "**", "*.txt")
        files_found = glob.glob(search_pattern, recursive=True)
        files_found = [f for f in files_found if 'desktop.ini' not in f]

        subject_groups = {}
        for file_path in files_found:
            filename = os.path.basename(file_path)
            parts = filename.split('_')
            subject_id = parts[1] if len(parts) >= 2 else "Unknown"
            if subject_id not in subject_groups: subject_groups[subject_id] = []
            subject_groups[subject_id].append(file_path)

        train, test = [], []
        for group in subject_groups.values():
            if len(group) == 1:
                if random.random() >= ratio:
                    test.extend(group)
                else:
                    train.extend(group)
            else:
                random.shuffle(group)
                split_point = int(len(group) * ratio)
                train.extend(group[:split_point])
                test.extend(group[split_point:])
        return train, test

    def __read_data(self, data_path):
        try:
            data = pd.read_csv(data_path, header=None)
            if data.shape[1] < 9: return pd.DataFrame()

            # 1. Downsample 200Hz -> 50Hz (Take every 4th sample)
            data = data.iloc[::4, :].reset_index(drop=True)

            # 2. Extract and Scale to 'g' units
            # SisFall ADXL345 is 13-bit, +/-16g -> ~4mg/LSB (0.004)
            # This makes the numbers match your ESP32 (which reads ~1.0 for gravity)
            acc_data = data[[0, 1, 2]].astype(float) * 0.004

            acc_data.columns = ['ax', 'ay', 'az']
            return acc_data
        except:
            return pd.DataFrame()

    def datasets_to_nparray(self, files):
        collection = []
        for file in tqdm(files, ncols=80):
            df = self.__read_data(file)
            if not df.empty:
                label = 1 if os.path.basename(file).startswith('F') else 0
                arr = df.to_numpy()
                labels = np.full((len(arr), 1), label)
                combined = np.hstack((arr, labels))
                collection.append(combined)
        return collection

    def windowing2d(self, raw_data_list, window_size=200, overlap_ratio=0.5):
        features, labels = [], []
        step = int(window_size * (1 - overlap_ratio))

        for data in raw_data_list:
            for i in range(0, len(data) - window_size, step):
                window = data[i: i + window_size]
                feats = window[:, :3]
                lbls = window[:, 3]
                label = 1 if np.sum(lbls) > 0 else 0
                features.append(feats.flatten())
                labels.append(label)
        return np.array(features), np.array(labels)


if __name__ == "__main__":
    # CHECK THIS PATH
    path = "../SisFall_dataset/"

    proc = DatasetProcessor()
    print("Step 1: Finding files...")
    if os.path.exists(path):
        train_files, test_files = proc.get_file_name(path)

        print("Step 2: Processing (Scaling to 'g' + Downsampling)...")
        raw_train = proc.datasets_to_nparray(train_files)
        raw_test = proc.datasets_to_nparray(test_files)

        print("Step 3: Windowing...")
        X_train, y_train = proc.windowing2d(raw_train, window_size=200, overlap_ratio=0.5)
        X_test, y_test = proc.windowing2d(raw_test, window_size=200, overlap_ratio=0.5)

        print("Step 4: Saving...")
        np.savez_compressed("processed_data.npz", X_train=X_train, y_train=y_train, X_test=X_test, y_test=y_test)
        print("✅ Data Ready!")
    else:
        print(f"❌ Error: Folder not found at {os.path.abspath(path)}")