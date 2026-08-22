#!/usr/bin/env python3
"""
Vital Care Referral Form Filler
Fills PDF referral forms with patient and provider information
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime
import subprocess
import tempfile

# Field mapping for each referral form type
# Maps common field names to PDF-specific field IDs
FIELD_MAPPINGS = {
    'IG': {
        'firstName': 'Date 4',
        'lastName': 'Date 3',
        'dob': 'Date 5',
        'phone': 'Date 9',
        'gender': 'Gender',
        'weight': 'Date 37',
        'height': 'Date 36',
        'address': 'Date 32',
        'city': 'Date 38',
        'state': 'Date 39',
        'zip': 'Date 40',
        'allergies': 'Date 41',
        'ssn': 'Date 42',
        'insurancePlan': 'Date 33',
        'policyNumber': 'Date 34',
        'planId': 'Date 35',
        'prescriberName': 'Date 31',
        'npi': 'Date 48',
        'practice': 'Date 47',
        'prescriberPhone': 'Date 49',
        'prescriberFax': 'Date 50',
        'prescriberEmail': 'Date 51',
        'diagnosis': 'Date 44',
        'medication': 'Date 52',
        'dose': 'Date 53',
        'vascularAccess': 'Date 54',
        'pharmacyName': 'Pharmacy Name',
        'pharmacyPhone': 'Phone',
        'pharmacyFax': 'Fax',
        'pharmacyEmail': 'Email',
    },
    # Add other form types as needed
    'IVABx': {
        'firstName': 'Patient Name',  # Will need to extract actual field names
        'lastName': 'Patient Name',
        'dob': 'DOB',
        'diagnosis': 'Diagnosis/ICD-10',
        'medication': 'Medication',
        'prescriberName': 'Prescriber',
        'npi': 'NPI',
    },
    'TPN': {
        'firstName': 'Patient Name',
        'lastName': 'Patient Name',
        'dob': 'Date of Birth',
        'diagnosis': 'Diagnosis',
        'prescriberName': 'Physician signing discharge orders',
    },
}

def get_form_file(form_type):
    """Get the PDF file path for a form type."""
    files = {
        'Alpha1': 'a1Therapy.pdf',
        'Dermatology': 'Dermatology.pdf',
        'Enteral': 'Enteral.pdf',
        'GI': 'GI.pdf',
        'HomeInfusion': 'HomeInfusion.pdf',
        'IG': 'IG.pdf',
        'ImmuneDeficiency': 'ImmuneDeficiencyIG.pdf',
        'IVABx': 'IVABx.pdf',
        'Neurology': 'Neurology.pdf',
        'Rheumatology': 'Rheumatology.pdf',
        'TPN': 'TPN.pdf',
    }
    return files.get(form_type)

def create_field_values_file(user_data, form_type, mapping):
    """Create a field_values.json file for the PDF filling script."""
    field_values = []
    
    for common_name, value in user_data.items():
        if not value:
            continue
            
        pdf_field_id = mapping.get(common_name)
        if not pdf_field_id:
            continue
        
        field_values.append({
            'field_id': pdf_field_id,
            'description': common_name,
            'value': str(value)
        })
    
    return field_values

def fill_pdf(form_type, user_data, output_file):
    """Fill a PDF form with user data."""
    
    # Get form file
    form_file = get_form_file(form_type)
    if not form_file:
        raise ValueError(f"Unknown form type: {form_type}")
    
    # Find the PDF file
    uploads_dir = Path('/mnt/user-data/uploads')
    pdf_path = uploads_dir / form_file
    
    if not pdf_path.exists():
        raise FileNotFoundError(f"Form file not found: {pdf_path}")
    
    # Get field mapping (use basic mapping for IG as default)
    mapping = FIELD_MAPPINGS.get(form_type, FIELD_MAPPINGS.get('IG', {}))
    
    # Create field values
    field_values = create_field_values_file(user_data, form_type, mapping)
    
    if not field_values:
        raise ValueError("No valid field values provided")
    
    # Create temporary files for the fill process
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(field_values, f)
        field_values_file = f.name
    
    try:
        # Use the PDF skills fill script
        pdf_skills_dir = Path('/mnt/skills/public/pdf')
        fill_script = pdf_skills_dir / 'scripts' / 'fill_fillable_fields.py'
        
        if not fill_script.exists():
            raise FileNotFoundError(f"Fill script not found: {fill_script}")
        
        # Run the fill script
        result = subprocess.run(
            [sys.executable, str(fill_script), str(pdf_path), field_values_file, str(output_file)],
            capture_output=True,
            text=True,
            cwd=str(pdf_skills_dir)
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"PDF fill failed: {result.stderr}")
        
        return True
        
    finally:
        # Clean up temporary files
        if os.path.exists(field_values_file):
            os.remove(field_values_file)

def main():
    """Main function to handle form filling."""
    
    if len(sys.argv) < 2:
        print("Usage: python fill_referral_forms.py <form_type> <output_file> [data_json_file]")
        print("\nForm types:")
        for form_type in ['IG', 'IVABx', 'TPN', 'Alpha1', 'Dermatology', 'Enteral', 'GI', 'HomeInfusion', 'ImmuneDeficiency', 'Neurology', 'Rheumatology']:
            print(f"  - {form_type}")
        print("\nExample:")
        print("  python fill_referral_forms.py IG output.pdf data.json")
        sys.exit(1)
    
    form_type = sys.argv[1]
    output_file = sys.argv[2]
    
    # Load user data
    user_data = {}
    if len(sys.argv) > 3:
        with open(sys.argv[3], 'r') as f:
            user_data = json.load(f)
    
    try:
        print(f"Filling {form_type} referral form...")
        fill_pdf(form_type, user_data, output_file)
        print(f"✓ Successfully created: {output_file}")
        print(f"  Ready to print and fax to: (513) 780-5881")
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
