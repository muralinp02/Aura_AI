# preprocessing.py
from __future__ import annotations
import os
import pandas as pd
from typing import Optional, Tuple, List
from sklearn.preprocessing import MinMaxScaler, LabelEncoder
import joblib

# Canonical MDP/KDD-style columns (41 features + label + difficulty)
MDP_COLUMNS: List[str] = [
    'duration','protocol_type','service','flag','src_bytes','dst_bytes','land','wrong_fragment','urgent',
    'hot','num_failed_logins','logged_in','num_compromised','root_shell','su_attempted','num_root',
    'num_file_creations','num_shells','num_access_files','num_outbound_cmds','is_host_login','is_guest_login',
    'count','srv_count','serror_rate','srv_serror_rate','rerror_rate','srv_rerror_rate','same_srv_rate',
    'diff_srv_rate','srv_diff_host_rate','dst_host_count','dst_host_srv_count','dst_host_same_srv_rate',
    'dst_host_diff_srv_rate','dst_host_same_src_port_rate','dst_host_srv_diff_host_rate','dst_host_serror_rate',
    'dst_host_srv_serror_rate','dst_host_rerror_rate','dst_host_srv_rerror_rate','label','difficulty'
]

CATEGORICAL_COLS = ['protocol_type', 'service', 'flag']
LABEL_COL = 'label'
DROP_IF_PRESENT = ['difficulty']

_THIS_DIR = os.path.dirname(__file__)
_MODELS_DIR = os.path.abspath(os.path.join(_THIS_DIR, "..", "backend", "models"))
# Fallback if running directly inside backend/
if not os.path.isdir(_MODELS_DIR):
    _MODELS_DIR = os.path.abspath(os.path.join(_THIS_DIR, "models"))

_ENCODERS_PATH = os.path.join(_MODELS_DIR, "encoders.joblib")   # dict[str, LabelEncoder]
_SCALER_PATH   = os.path.join(_MODELS_DIR, "scaler.joblib")     # MinMaxScaler

def _read_any_mdp_csv(input_path: str) -> pd.DataFrame:
    # Try headerless with expected width
    try:
        df = pd.read_csv(input_path, header=None)
        if df.shape[1] == len(MDP_COLUMNS):
            df.columns = MDP_COLUMNS
            return df
    except Exception:
        pass
    # Fallback: with header
    return pd.read_csv(input_path)

def _load_artifacts():
    encoders = None
    scaler = None
    if os.path.exists(_ENCODERS_PATH):
        try:
            encoders = joblib.load(_ENCODERS_PATH)
            if not isinstance(encoders, dict):
                encoders = None
        except Exception:
            encoders = None
    if os.path.exists(_SCALER_PATH):
        try:
            scaler = joblib.load(_SCALER_PATH)
        except Exception:
            scaler = None
    return encoders, scaler

def _fit_or_transform_cats(df: pd.DataFrame, encoders_in):
    encoders = {} if encoders_in is None else dict(encoders_in)
    for col in CATEGORICAL_COLS:
        if col not in df.columns:
            df[col] = "unknown"
        df[col] = df[col].astype(str)
        if col not in encoders:
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col])
            encoders[col] = le
        else:
            le = encoders[col]
            known = set(le.classes_)
            unseen = sorted(set(df[col].unique()) - known)
            if unseen:
                le.classes_ = pd.Index(list(le.classes_) + unseen)
            df[col] = le.transform(df[col])
    return df, encoders

def _fit_or_transform_scale(df_feat: pd.DataFrame, scaler_in: Optional[MinMaxScaler]):
    if scaler_in is None:
        scaler = MinMaxScaler()
        arr = scaler.fit_transform(df_feat.values)
    else:
        scaler = scaler_in
        arr = scaler.transform(df_feat.values)
    out = pd.DataFrame(arr, columns=df_feat.columns, index=df_feat.index)
    return out, scaler

def preprocess_mdp(input_path: str) -> pd.DataFrame:
    """
    Read raw MDP-like file and return FEATURES-ONLY DataFrame ready for model.predict(...).
    - Drops 'difficulty' and 'label' if present
    - Encodes protocol/service/flag with persisted encoders (if exist), else fits ad-hoc
    - Scales all numeric columns with persisted scaler (if exists), else fits ad-hoc
    """
    df = _read_any_mdp_csv(input_path).copy()

    for c in DROP_IF_PRESENT:
        if c in df.columns:
            df.drop(columns=[c], inplace=True)

    if LABEL_COL in df.columns:
        df.drop(columns=[LABEL_COL], inplace=True)

    encoders, scaler = _load_artifacts()
    df, _ = _fit_or_transform_cats(df, encoders)

    # numeric + fillna
    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.fillna(0.0)

    df_scaled, _ = _fit_or_transform_scale(df, scaler)
    return df_scaled

# Optional batch runner
def preprocess_mdp_to_file(input_path: str, output_path: str) -> pd.DataFrame:
    df = preprocess_mdp(input_path)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    return df

if __name__ == "__main__":
    raw_dir = os.path.join(_THIS_DIR, '..', 'data', 'raw')
    processed_dir = os.path.join(_THIS_DIR, '..', 'data', 'processed')
    os.makedirs(processed_dir, exist_ok=True)

    train_in = os.path.join(raw_dir, 'MDPTrain+.txt')
    test_in  = os.path.join(raw_dir, 'MDPTest+.txt')
    train_out = os.path.join(processed_dir, 'train.csv')
    test_out  = os.path.join(processed_dir, 'test.csv')

    if os.path.exists(train_in):
        print("[preprocessing] writing:", train_out)
        preprocess_mdp_to_file(train_in, train_out)
    if os.path.exists(test_in):
        print("[preprocessing] writing:", test_out)
        preprocess_mdp_to_file(test_in, test_out)
