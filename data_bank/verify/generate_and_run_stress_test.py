import os
import sys
import json
import difflib
from decimal import Decimal
from google.auth import default
from google.cloud import bigquery, discoveryengine_v1 as discoveryengine

print("Script template ready")
