import pandas as pd
import os

def calculate_traffic(input_file):
    # Load the data
    df = pd.read_excel(input_file)
    
    # Print first few rows to verify CTR values
    print("First few rows of the data:")
    print(df.head())
    
    # Ensure CTR column is in correct format and handle potential errors
    df['CTR'] = pd.to_numeric(df['CTR'], errors='coerce')
    df['CTR'] = df['CTR'].fillna(0)  # Replace NaN with 0
    
    # Calculate traffic without converting CTR (assuming CTR is already in decimal form)
    df['Lower Traffic'] = df['Показы'] * (df['CTR'] * 0.8)
    df['Upper Traffic'] = df['Показы'] * (df['CTR'] * 1.2)
    df['Average Traffic'] = df['Показы'] * df['CTR']
    
    # Calculate daily traffic
    df['Lower Daily Traffic'] = df['Lower Traffic'] / 30
    df['Upper Daily Traffic'] = df['Upper Traffic'] / 30
    df['Average Daily Traffic'] = df['Average Traffic'] / 30
    
    # Generate output file path
    output_file = os.path.splitext(input_file)[0] + '_traffic_forecast.xlsx'
    
    # Save to a new Excel file
    df.to_excel(output_file, index=False)
    print(f'Results saved to {output_file}')

# Example usage
input_file = '/Users/dmitrijkovalev/Downloads/brostore/smartphony_samsung.xlsx' # Replace with your input file path
calculate_traffic(input_file)