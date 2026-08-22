"""
Vital Care Referral Form Filler - Flask Backend
Fills PDF forms and returns downloadable PDFs
"""

from flask import Flask, request, jsonify, send_file
import json
import subprocess
import tempfile
import os
from pathlib import Path
import traceback
from datetime import datetime

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max

REFERRAL_TYPES = {
    'IG': 'IG.pdf',
    'IVABx': 'IVABx.pdf',
    'TPN': 'TPN.pdf',
    'Alpha1': 'a1Therapy.pdf',
    'Dermatology': 'Dermatology.pdf',
    'Enteral': 'Enteral.pdf',
    'GI': 'GI.pdf',
    'HomeInfusion': 'HomeInfusion.pdf',
    'ImmuneDeficiency': 'ImmuneDeficiencyIG.pdf',
    'Neurology': 'Neurology.pdf',
    'Rheumatology': 'Rheumatology.pdf',
}

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
}

def get_pdf_path(form_type):
    """Get path to the PDF template."""
    if form_type not in REFERRAL_TYPES:
        return None
    pdf_name = REFERRAL_TYPES[form_type]
    return Path(__file__).parent.parent / 'pdfs' / pdf_name

def create_field_values(form_data, form_type):
    """Create field_values.json for PDF filling."""
    mapping = FIELD_MAPPINGS.get(form_type, {})
    field_values = []
    
    for common_name, value in form_data.items():
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

def fill_pdf_form(pdf_path, form_data, form_type):
    """Fill a PDF form with data."""
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        raise ImportError("pypdf not installed. Run: pip install pypdf")
    
    field_values = create_field_values(form_data, form_type)
    
    if not field_values:
        raise ValueError("No fields to fill")
    
    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()
    
    # Get form fields from PDF
    if "/AcroForm" not in reader.trailer["/Root"]:
        raise ValueError("PDF has no fillable form fields")
    
    # Copy all pages
    for page in reader.pages:
        writer.add_page(page)
    
    # Try to update form fields
    if writer._root_object["/AcroForm"]["/Fields"]:
        for field_value in field_values:
            try:
                writer.update_page_form_field_values(
                    writer.pages[0],
                    {field_value['field_id']: field_value['value']}
                )
            except Exception as e:
                print(f"Warning: Could not fill field {field_value['field_id']}: {e}")
    
    # Write to temporary file
    output_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
    writer.write(output_file)
    output_file.close()
    
    return output_file.name

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok',
        'service': 'Vital Care Referral Form Filler',
        'timestamp': datetime.utcnow().isoformat()
    }), 200

@app.route('/api/forms', methods=['GET'])
def list_forms():
    """List available referral form types."""
    return jsonify({
        'forms': [
            {'id': k, 'name': k} for k in sorted(REFERRAL_TYPES.keys())
        ]
    }), 200

@app.route('/api/fill', methods=['POST'])
def fill_form():
    """Fill a referral form with patient data and return PDF."""
    try:
        data = request.json
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        form_type = data.get('formType')
        form_data = data.get('formData', {})
        
        if not form_type:
            return jsonify({'error': 'formType is required'}), 400
        
        if form_type not in REFERRAL_TYPES:
            return jsonify({
                'error': f'Unknown form type: {form_type}',
                'available': list(REFERRAL_TYPES.keys())
            }), 400
        
        # Get PDF path
        pdf_path = get_pdf_path(form_type)
        if not pdf_path or not pdf_path.exists():
            return jsonify({'error': f'PDF template not found: {form_type}'}), 404
        
        # Fill the form
        output_file = fill_pdf_form(pdf_path, form_data, form_type)
        
        # Prepare download filename
        last_name = form_data.get('lastName', 'patient').replace(' ', '_')
        filename = f"referral_{form_type}_{last_name}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        try:
            # Send the file
            return send_file(
                output_file,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=filename
            )
        finally:
            # Cleanup will happen when response is sent
            pass
    
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(f"Error: {error_msg}")
        return jsonify({'error': 'Failed to generate PDF', 'details': str(e)}), 500

@app.route('/api/summary', methods=['POST'])
def generate_summary():
    """Generate a text summary of the referral information."""
    try:
        data = request.json
        form_data = data.get('formData', {})
        form_type = data.get('formType', 'Unknown')
        
        summary = f"""
📋 VITAL CARE REFERRAL SUMMARY
═══════════════════════════════════════════════════════

REFERRAL TYPE: {form_type}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

PATIENT INFORMATION:
  Name: {form_data.get('firstName', 'N/A')} {form_data.get('lastName', 'N/A')}
  DOB: {form_data.get('dob', 'N/A')}
  Phone: {form_data.get('phone', 'N/A')}
  SSN (last 4): {form_data.get('ssn', 'N/A')}
  Gender: {form_data.get('gender', 'N/A')}
  Weight: {form_data.get('weight', 'N/A')} kg
  Height: {form_data.get('height', 'N/A')}
  Address: {form_data.get('address', 'N/A')}
  City/State/Zip: {form_data.get('city', '')}, {form_data.get('state', '')} {form_data.get('zip', '')}
  Allergies: {form_data.get('allergies', 'None')}

INSURANCE INFORMATION:
  Plan: {form_data.get('insurancePlan', 'N/A')}
  Policy #: {form_data.get('policyNumber', 'N/A')}
  Plan ID: {form_data.get('planId', 'N/A')}

PRESCRIBER INFORMATION:
  Name: {form_data.get('prescriberName', 'N/A')}
  NPI: {form_data.get('npi', 'N/A')}
  Practice: {form_data.get('practice', 'N/A')}
  Phone: {form_data.get('prescriberPhone', 'N/A')}
  Fax: {form_data.get('prescriberFax', 'N/A')}
  Email: {form_data.get('prescriberEmail', 'N/A')}

CLINICAL INFORMATION:
  Diagnosis (ICD-10): {form_data.get('diagnosis', 'N/A')}
  Medication: {form_data.get('medication', 'N/A')}
  Dose/Frequency: {form_data.get('dose', 'N/A')}
  Vascular Access: {form_data.get('vascularAccess', 'N/A')}
  Clinical Notes: {form_data.get('clinicalNotes', 'None')}

PHARMACY INFORMATION:
  Name: {form_data.get('pharmacyName', 'N/A')}
  Phone: {form_data.get('pharmacyPhone', 'N/A')}
  Fax: {form_data.get('pharmacyFax', 'N/A')}
  Email: {form_data.get('pharmacyEmail', 'N/A')}

═══════════════════════════════════════════════════════
TO SUBMIT:
1. Download the filled PDF using the button above
2. Review all information for accuracy
3. Print the form
4. Fax to: (513) 780-5881

For support, contact Vital Care at:
  Phone: (513) 780-5880
  Fax: (513) 780-5881
"""
        return jsonify({'summary': summary}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/', methods=['GET'])
def index():
    """Return API documentation."""
    return jsonify({
        'name': 'Vital Care Referral Form Filler API',
        'version': '1.0.0',
        'endpoints': {
            'GET /api/health': 'Health check',
            'GET /api/forms': 'List available form types',
            'POST /api/fill': 'Fill form and return PDF',
            'POST /api/summary': 'Generate text summary'
        },
        'usage': {
            'fill': {
                'method': 'POST',
                'url': '/api/fill',
                'body': {
                    'formType': 'IG',
                    'formData': {
                        'firstName': 'John',
                        'lastName': 'Doe',
                        'dob': '01/15/1990',
                        '...': 'other fields'
                    }
                }
            }
        }
    }), 200

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
