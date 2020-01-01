import pickle
import threading


class Datastore:
    def __init__(self, file):
        self.file = file
        self.data = {}
        self.lock = threading.Lock()

        try:
            with open(self.file, 'rb') as f:
                try:
                    self.data = pickle.load(f)  # Load data, or initialize data to {}
                except:
                    self.data = {}
                    self.save_data()
        except FileNotFoundError:
            self.data = {}

    def set(self, key, value):
        self.lock.acquire()
        self.data[key] = value
        self.save_data()
        self.lock.release()

    def get(self, item):
        try:
            return self.data[item]
        except KeyError:
            return None

    def save_data(self):
        with open(self.file, 'wb') as file:  # Save data
            pickle.dump(self.data, file)
