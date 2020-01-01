import pickle


class Datastore:
    def __init__(self, file):
        self.file = file
        self.data = {}

        try:
            with open(self.file, 'rb') as f:
                try:
                    self.data = pickle.load(f)  # Load data, or initialize data to {}
                except pickle.PickleError:
                    self.data = {}
                    self.save_data()
        except FileNotFoundError:
            self.data = {}

    def set(self, key, value):
        self.data[key] = value
        self.save_data()

    def get(self, item):
        try:
            return self.data[item]
        except KeyError:
            return None

    def save_data(self):
        with open(self.file, 'wb') as file:  # Save data
            pickle.dump(self.data, file)
