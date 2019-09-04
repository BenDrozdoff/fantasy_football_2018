from sklearn.base import TransformerMixin


class DfColumnSelector(TransformerMixin):
    def __init__(self, column_name):
        self.column_name = column_name
        
    def fit(self, x, y=None):
        return self
    
    def transform(self, x):
        return x[self.column_name].values.reshape(-1,1)