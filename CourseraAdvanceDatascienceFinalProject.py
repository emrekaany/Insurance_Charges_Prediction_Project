# -*- coding: utf-8 -*-
"""
Created on Fri Jun  7 12:10:28 2024

@author: ky4642
"""

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, BatchNormalization, Dropout
from bayes_opt import BayesianOptimization
import numpy as np
from sklearn.metrics import mean_squared_error
import mpld3
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression

# Load the dataset from the CSV file
# Replace 'path_to_file.csv' with the actual path to the CSV file
file_path = 'C:\\Users\\ky4642\\Downloads\\insurance.csv'
df = pd.read_csv(file_path)

#####
# Part: Data Quality Checks
#####

print("Corrupts in data are as following")

# Checking for missing values
print(f"Number of null values found: {df.isnull().sum()}")

# Checking for duplicates
print(f"Number of duplicated values found: {df.duplicated().sum()}")

# Check for invalid age values (age < 0)
invalid_age = df[df['age'] < 0]

# Check for valid BMI values (BMI should be within reasonable range)
invalid_bmi = df[(df['bmi'] < 10) | (df['bmi'] > 50)]

# Check for invalid children count (non-negative values)
invalid_children = df[df['children'] < 0]

# Output the results of the checks
print(f"Number of invalid ages found: {invalid_age.shape[0]}")
print(f"Number of invalid BMI values found: {invalid_bmi.shape[0]}")
print(f"Invalid children counts found: {invalid_children.shape[0]}")

# Remove corrupted rows based on previous checks
df = df.dropna()  # Remove rows with missing values
df = df[df['age'] > 0]  # Remove rows with invalid age
df = df[(df['bmi'] > 10) & (df['bmi'] < 50)]  # Keep only rows with valid BMI
df = df[df['children'] > 0]  # Keep rows with valid children count

########
# Part: Encoding categorical columns and creating a new feature
########

# Convert categorical columns ('sex', 'smoker', 'region') into numerical codes
for column in ['sex', 'smoker', 'region']:
    df[column + '_encoded'] = df[column].astype('category').cat.codes

# Create a new feature 'number_of_times_gave_birth' based on sex and number of children
df['number_of_times_gave_birth'] = (1 - df['sex_encoded']) * df['children']

# Drop the original categorical columns from the dataset
df_featured = df.drop(columns=['sex', 'smoker', 'region'])

# Print the first few rows of the DataFrame to confirm data
print(df_featured)

# Calculate the correlation matrix to determine which columns may be unnecessary for feature selection
correlation_matrix = df_featured.corr()
correlation_with_target = correlation_matrix['charges'].sort_values()

# Print correlations between features and target variable 'charges'
print(correlation_with_target)

# Drop columns with low correlation (optional step)
low_correlation_cols = correlation_with_target[correlation_with_target.abs() < 0.1].index  # threshold can vary
df_featured = df_featured.drop(columns=low_correlation_cols)

#########
# Part: Plots for Data Visualization
#########

# Create a list to store HTML versions of the plots
plots_html = []

# Scatter plot for Age vs. Charges by Smoking Status
plt.figure(figsize=(10, 6))
sns.scatterplot(x='age', y='charges', hue='smoker_encoded', data=df, palette=['red', 'green'], style='smoker_encoded', markers=['o', 'X'])
plt.title('Age vs. Charges by Smoking Status')
plt.xlabel('Age')
plt.ylabel('Charges')
plt.legend(title='Smoker')
plt.close()

# Box plot for Charges by Region
plt.figure(figsize=(12, 6))
sns.boxplot(x='region_encoded', y='charges', data=df)
plt.title('Medical Charges by Region')
plt.xlabel('Region')
plt.ylabel('Charges')
plots_html.append(mpld3.fig_to_html(plt.gcf()))  # Save the plot as HTML
plt.close()

# Heat map of the correlation matrix
plt.figure(figsize=(10, 8))
columns = ['age', 'bmi', 'children', 'charges', 'sex_encoded', 'smoker_encoded', 'region_encoded', 'number_of_times_gave_birth']
corr_matrix = df[['age', 'bmi', 'children', 'charges', 'sex_encoded', 'smoker_encoded', 'region_encoded', 'number_of_times_gave_birth']].corr()
sns.heatmap(corr_matrix, annot=True, fmt=".2f", cmap='coolwarm', xticklabels=columns, yticklabels=columns)
plt.title('Correlation Matrix')
ticks = np.arange(len(columns)) + 0.5
plt.xticks(ticks=ticks, labels=columns, rotation=45)
plt.yticks(ticks=ticks, labels=columns, rotation=0)
plots_html.append(mpld3.fig_to_html(plt.gcf()))  # Save the plot as HTML
plt.close()

# Scatter plot for BMI vs. Charges
plt.figure(figsize=(10, 6))
sns.scatterplot(x='bmi', y='charges', data=df, hue='smoker_encoded')
plt.title('BMI vs. Charges by Smoking Status')
plt.xlabel('BMI')
plt.ylabel('Charges')
plots_html.append(mpld3.fig_to_html(plt.gcf()))  # Save the plot as HTML
plt.close()

# Line plot for Average Charges by Age (Grouped by Smoker Status)
average_charges = df.groupby(['age', 'smoker_encoded'])['charges'].mean().unstack()
plt.figure(figsize=(12, 6))
average_charges.plot(kind='line')
plt.title('Average Charges by Age and Smoker Status')
plt.xlabel('Age')
plt.ylabel('Average Charges')
plt.legend(title='Smoker')
plots_html.append(mpld3.fig_to_html(plt.gcf()))  # Save the plot as HTML
plt.close()

#########
# Part: Data Scaling and Splitting
#########

# Define features (X) and target (y)
X = df_featured.drop(columns=['charges'])  # Features
y = df_featured['charges']  # Target variable

# Reshape target variable into a 2D array
y = np.array(y).reshape(-1, 1)

# Scale the features and target
Xscaler = MinMaxScaler()
Yscaler = MinMaxScaler()
X = pd.DataFrame(Xscaler.fit_transform(X), columns=X.columns)
y = pd.DataFrame(Yscaler.fit_transform(y))

# Split the data into training, validation, and test sets
X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.3, random_state=42)
X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42)

#########
# Part: Model Training and Optimization
#########

# Initialize a DataFrame to track model performance
df_performances = pd.DataFrame({
    'Model': [],
    'Training_MAPE': [],
    'Validation_MAPE': [],
    'Testing_MAPE': []
})

# Define a Keras model for use with Bayesian Optimization
def keras_model(n_units, dropout_rate, optimizer_index):
    optimizers = ['adam', 'sgd']
    optimizer = optimizers[int(optimizer_index)]
    
    # Build a simple fully connected neural network
    model = Sequential([
        Dense(int(n_units), activation='relu', input_shape=(X_train.shape[1],)),
        Dropout(dropout_rate),
        Dense(int(n_units), activation='relu'),
        Dropout(dropout_rate),
        Dense(1)
    ])
    model.compile(optimizer=optimizer, loss='mean_squared_error')
    
    # Train the model
    model.fit(X_train, y_train, epochs=10, batch_size=32, verbose=0, validation_data=(X_val, y_val))
    
    # Return negative mean squared error (for maximization)
    mse = model.evaluate(X_val, y_val, verbose=0)
    return -mse

# Wrapper function for Bayesian Optimization
def objective(n_units, dropout_rate, optimizer_index):
    return keras_model(n_units, dropout_rate, optimizer_index)

# Define the parameter bounds for Bayesian Optimization
pbounds = {
    'n_units': (32, 128),  # Number of units in a layer
    'dropout_rate': (0.1, 0.5),  # Dropout rate
    'optimizer_index': (0, 1)  # Index to select optimizer
}

# Perform Bayesian Optimization
optimizer = BayesianOptimization(
    f=objective,
    pbounds=pbounds,
    random_state=1,
)
optimizer.maximize(init_points=2, n_iter=10)

# Train the final model using the best parameters
best_parameters = optimizer.max['params']
model = Sequential([
    Dense(int(best_parameters['n_units']), activation='relu', input_shape=(X_train.shape[1],)),
    Dropout(best_parameters['dropout_rate']),
    Dense(int(best_parameters['n_units']), activation='relu'),
    Dropout(best_parameters['dropout_rate']),
    Dense(1)
])
model.compile(loss='mean_squared_error')

# Train the model
model.fit(X_train, y_train, epochs=10, batch_size=32, verbose=0, validation_data=(X_val, y_val))

# Make predictions on the test set
y_pred = model.predict(X_test)
y_pred = Yscaler.inverse_transform(y_pred)
y_test = Yscaler.inverse_transform(y_test)

# Function to calculate MAPE (Mean Absolute Percentage Error)
def mean_absolute_percentage_error(y_true, y_pred):
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    return np.mean(np.abs((y_true - y_pred) / y_true)) * 100

# Calculate MAPE for the neural network model
mape = mean_absolute_percentage_error(y_test, y_pred)
print("MAPE ratio for Fully Connected Neural Network model on feature selected data is :" + str(mape))

# Add the model's performance to the performance tracking DataFrame
new_row = pd.DataFrame({
    'Model': ['Fully Connected Neural Network model on feature selected data'],
    'Training_MAPE': [mean_absolute_percentage_error(Yscaler.inverse_transform(y_train), Yscaler.inverse_transform(model.predict(X_train)))],
    'Validation_MAPE': [mean_absolute_percentage_error(Yscaler.inverse_transform(y_val), Yscaler.inverse_transform(model.predict(X_val)))],
    'Testing_MAPE': [mape]
})
df_performances = pd.concat([df_performances, new_row], ignore_index=True)

#########
# Part: Training Other Models (Linear Regression, Random Forest)
#########

# Train and evaluate a Linear Regression model
lr = LinearRegression()
lr.fit(X_train, y_train)
y_pred_lr = lr.predict(X_test)
y_pred_lr = Yscaler.inverse_transform(y_pred_lr)
y_test = Yscaler.inverse_transform(y_test)
mape_lr = mean_absolute_percentage_error(y_test, y_pred_lr)
print("MAPE ratio for Linear Regression model on feature selected data is :" + str(mape_lr))

# Add Linear Regression results to performance DataFrame
new_row = pd.DataFrame({
    'Model': ['Linear Regression model on feature selected data'],
    'Training_MAPE': [mean_absolute_percentage_error(Yscaler.inverse_transform(y_train), Yscaler.inverse_transform(lr.predict(X_train)))],
    'Validation_MAPE': [mean_absolute_percentage_error(Yscaler.inverse_transform(y_val), Yscaler.inverse_transform(lr.predict(X_val)))],
    'Testing_MAPE': [mape_lr]
})
df_performances = pd.concat([df_performances, new_row], ignore_index=True)

# Train and evaluate a Random Forest Regressor model
rf = RandomForestRegressor(n_estimators=100, random_state=42)
rf.fit(X_train, y_train)
y_pred_RF = rf.predict(X_test)
y_pred_RF = Yscaler.inverse_transform(y_pred_RF.reshape(-1, 1))
y_test = Yscaler.inverse_transform(y_test)
mape_RF = mean_absolute_percentage_error(y_test, y_pred_RF)
print("MAPE ratio for Random Forest Regressor model on feature selected data is :" + str(mape_RF))

# Add Random Forest results to performance DataFrame
new_row = pd.DataFrame({
    'Model': ['Random Forest Regressor model on feature selected data'],
    'Training_MAPE': [mean_absolute_percentage_error(Yscaler.inverse_transform(y_train), Yscaler.inverse_transform(rf.predict(X_train).reshape(-1, 1)))],
    'Validation_MAPE': [mean_absolute_percentage_error(Yscaler.inverse_transform(y_val), Yscaler.inverse_transform(rf.predict(X_val).reshape(-1, 1)))],
    'Testing_MAPE': [mape_RF]
})
df_performances = pd.concat([df_performances, new_row], ignore_index=True)

#########
# Part: Saving Plots and Results to HTML
#########

# Convert the performance DataFrame to HTML and append to the plots list
plots_html.append(df_performances.to_html(index=False))

# Save all plots and performance metrics into an HTML file
html_file = '<html><head><title>Insurance Data Visualizations</title></head><body>'
html_file += "\n".join(plots_html)
html_file += '</body></html>'

# Write the HTML content to a file
with open('C:\\Users\\ky4642\\Pictures\\visualizations.html', 'w') as f:
    f.write(html_file)
