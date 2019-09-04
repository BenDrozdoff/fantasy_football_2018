from xgboost import XGBRegressor
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.preprocessing import OneHotEncoder
from services.projection.data_cleaning.df_column_selector import DfColumnSelector


class FantasyRegressor():
    def __init__(self, target_column):
        self.target_column = target_column
        self.regressor = XGBRegressor(objective=self.objective())
        self.feature_pipeline = self.create_feature_pipeline()
        
    def fit(self, X):
        self.feature_matrix = self.feature_pipeline.fit_transform(X)
        self.regressor.fit(self.feature_matrix, X[self.target_column])
        return self
        
    def predict(self, x):
        regressor_input = self.feature_pipeline.transform(x)
        return self.regressor.predict(regressor_input)
        
    
    def create_feature_pipeline(self):
        return FeatureUnion([("Offense", self.nfl_team_pipeline("Offense")), 
                             ("Defense", self.nfl_team_pipeline("DefensiveTeam")),
                             ("Home", DfColumnSelector("OffenseIsHome"))
                            ])
    
    def objective(self):
        if any([string in self.target_column for string in ["RushYards", "PassYards"]]):
            objective = "reg:squarederror"
        elif "Pct" in self.target_column:
            objective = "reg:logistic"
        else:
            objective = "count:poisson"
        return objective
    
    def nfl_team_pipeline(self, column_name):
        return Pipeline(steps=[("select", DfColumnSelector(column_name)), ("encode", OneHotEncoder())])