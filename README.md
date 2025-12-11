# Organization Management Service (Backend Intern Assignment)

## Overview
FastAPI backend that allows creating and managing organizations in a multi-tenant style using MongoDB.
Master DB holds organization metadata and admin credentials; tenant data is stored in dynamic collections named `org_<organization_name>`.

## Requirements
- Python 3.9+
- MongoDB (running locally or accessible via URI)

## Setup
1. Clone the repository.
2. Create a Python virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate        # Linux/Mac
   venv\Scripts\activate           # Windows
