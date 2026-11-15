import requests
from dotenv import load_dotenv
import pandas as pd
import os
import re
import time
from typing import Optional, Any, Tuple
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from data.links import *

# Setup paths
BASE_DIR = Path(__file__).resolve().parents[2]

load_dotenv()

FREEZE = True  # Set to True to disable OnShape API calls

def extract_onshape_ids(url):
    parts = url.split('/')
    doc_idx = parts.index('documents') + 1
    workspace_idx = parts.index('w') + 1
    element_idx = parts.index('e') + 1
    
    return {
        'document_id': parts[doc_idx],
        'workspace_id': parts[workspace_idx],
        'element_id': parts[element_idx]
    }

class OnshapeAPI:
    """
    FREEZE = True:  CSV is source of truth. OnShape is never called.
                    set_variable updates CSV only.
    FREEZE = False: OnShape is live. get_all_variables syncs OnShape -> CSV.
                    set_variable pushes to OnShape then syncs CSV.
    """

    BASE_URL     = "https://cad.onshape.com"

    def __init__(self, url, file="data/placeholder.csv"):
        self.access_key = os.getenv('ONSHAPE_ACCESS_KEY')
        self.secret_key = os.getenv('ONSHAPE_SECRET_KEY')

        if not self.access_key or not self.secret_key:
            raise ValueError("Missing API keys! Check your .env file.")

        self.auth    = (self.access_key, self.secret_key)
        self.headers = {
            "Accept":       "application/json;charset=UTF-8; qs=0.09",
            "Content-Type": "application/json"
        }
        
        ids = extract_onshape_ids(url)
        self.DOCUMENT_ID = ids['document_id']
        self.WORKSPACE_ID = ids['workspace_id']
        self.ELEMENT_ID = ids['element_id']

        self.OUTPUT_PATH = BASE_DIR / file

    # ------------------------------------------------------------------
    # CSV helpers — always read/write fresh, no cache
    # ------------------------------------------------------------------

    def _read_csv(self) -> pd.DataFrame:
        if not self.OUTPUT_PATH.exists():
            raise FileNotFoundError(f"CSV not found: {self.OUTPUT_PATH}")
        return pd.read_csv(self.OUTPUT_PATH)

    def _write_csv(self, df: pd.DataFrame) -> None:
        self.OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(self.OUTPUT_PATH, index=False)

    # ------------------------------------------------------------------
    # OnShape API helpers
    # ------------------------------------------------------------------

    def _fetch_onshape(self) -> list:
        url = (f"{self.BASE_URL}/api/variables"
               f"/d/{self.DOCUMENT_ID}/w/{self.WORKSPACE_ID}/e/{self.ELEMENT_ID}/variables")
        response = requests.get(url, auth=self.auth, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def _push_onshape(self, variables: list) -> int:
        url = (f"{self.BASE_URL}/api/variables"
               f"/d/{self.DOCUMENT_ID}/w/{self.WORKSPACE_ID}/e/{self.ELEMENT_ID}/variables")
        response = requests.post(url, auth=self.auth, headers=self.headers, json=variables)
        return response.status_code

    def _onshape_to_df(self, data: list) -> pd.DataFrame:
        
        rows = []
        variables = data[0].get('variables', []) if data else []
        for var in variables:
            rows.append({
                'Name':          var.get('name', ''),
                'Variable type': var.get('type', ''),
                'Value':         var.get('expression', ''),
                'Description':   var.get('description', '')
            })
        df = pd.DataFrame(rows)
        if not df.empty:
            df = df[['Name', 'Variable type', 'Value', 'Description']]
        return df

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_all_variables(self) -> pd.DataFrame:
        """
        FREEZE=True:  Read CSV fresh and return it. No OnShape call.
        FREEZE=False: Fetch from OnShape, write to CSV, return it.
        """
        if FREEZE:
            print("FREEZE enabled. Reading csv ...")
            return self._read_csv()

        data = self._fetch_onshape()
        df   = self._onshape_to_df(data)
        self._write_csv(df)
        return df

    def set_variable(self, variable_name: str, new_value: Any) -> bool:
        """
        FREEZE=True:  Update CSV only.
        FREEZE=False: Push to OnShape, then sync CSV from OnShape.
        """
        if FREEZE:
            df = self._read_csv()
            if variable_name not in df['Name'].values:
                print(f"Variable '{variable_name}' not found in CSV.")
                return False
            df.loc[df['Name'] == variable_name, 'Value'] = str(new_value)
            self._write_csv(df)
            return True

        # Live: fetch latest, update, push, re-sync CSV
        data      = self._fetch_onshape()
        variables = data[0].get('variables', [])
        found     = False
        for var in variables:
            if var.get('name') == variable_name:
                var['expression'] = str(new_value)
                found = True
                break

        if not found:
            print(f"Variable '{variable_name}' not found in OnShape.")
            return False

        status = self._push_onshape(variables)
        if status != 204:
            raise RuntimeError(
                f"OnShape returned {status} for '{variable_name}' — update not confirmed."
            )

        # Re-sync CSV from OnShape to guarantee consistency
        df = self._onshape_to_df(data)
        self._write_csv(df)
        return True

    def set_variable_with_retry(self, name: str, value: Any, retries: int = 3, delay: int = 2):
        for attempt in range(retries):
            try:
                self.set_variable(name, value)
                return
            except Exception as e:
                print(f"  ⚠️  Attempt {attempt+1}/{retries} failed for '{name}': {e}")
                if attempt < retries - 1:
                    print(f"  🔄 Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    raise RuntimeError(
                        f"  ❌ Failed to set '{name}' after {retries} attempts."
                    ) from e

    def get_variable(self, variable_name: str) -> Optional[str]:
        """Returns raw expression string from CSV."""
        df     = self._read_csv()
        result = df[df['Name'] == variable_name]
        return result.iloc[0]['Value'] if not result.empty else None

    def get_variable_value(self, variable_name: str) -> Optional[Tuple[float, str]]:
        """Evaluates expression and returns (numeric_value, unit)."""
        expression = self.get_variable(variable_name)
        return self._evaluate_expression(expression) if expression else None

    def get_evaluated_variables_df(self) -> pd.DataFrame:
        """
        Always reads fresh from CSV (or OnShape if not FREEZE),
        evaluates all expressions, returns numeric dataframe.
        """
        df   = self.get_all_variables()
        rows = []
        for _, row in df.iterrows():
            result = self._evaluate_expression(row['Value'])
            val, unit = result if result else (None, None)
            rows.append({'Name': row['Name'], 'Value': val, 'Unit': unit})
        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # Expression evaluator
    # ------------------------------------------------------------------

    def _evaluate_expression(self, expression: str) -> Optional[Tuple[float, str]]:
        """Recursively evaluates OnShape expressions like '30 deg' or '#var + 5 mm'."""
        if not isinstance(expression, str):
            return None
        expression = expression.strip()

        if '#' in expression:
            var_refs = re.findall(r'#([a-zA-Z_][a-zA-Z0-9_]*)', expression)
            resolved = expression
            unit     = ''
            for ref in var_refs:
                evaluated = self.get_variable_value(ref)
                if not evaluated:
                    return None
                num_val, ref_unit = evaluated
                if not unit:
                    unit = ref_unit
                resolved = resolved.replace(f'#{ref}', str(num_val))
            try:
                result = eval(resolved, {"__builtins__": {}}, {})
                return (float(result), unit)
            except:
                return None
        else:
            parts = expression.split()
            try:
                val  = float(parts[0])
                unit = parts[1] if len(parts) == 2 else 'dimensionless'
                return (val, unit)
            except:
                return None


# ------------------------------------------------------------------
# Manual sync test
# ------------------------------------------------------------------


def test_onshape_sync_manual(url, file):
    api = OnshapeAPI(url, file)

    print("-" * 50)

    df = api.get_evaluated_variables_df()
    print(df)

    print("\n" + "="*50)
    print("🏁 Test complete.")


if __name__ == "__main__":
    test_onshape_sync_manual(INLET_LINK, INLET_FILE)