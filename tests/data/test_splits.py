import pandas as pd
from src.data.splits import solafune_like_split

# 1.1 Test : split déterministe

def test_split_is_deterministic():
    df = pd.DataFrame({
        "geolocation_name": ["A", "A", "B", "B"],
        "quarter_label": ["Q1", "Q2", "Q1", "Q2"],
        "value": [1, 2, 3, 4],
    })

    train1, test1 = solafune_like_split(df, seed="v1")
    train2, test2 = solafune_like_split(df, seed="v1")

    assert test1.index.tolist() == test2.index.tolist()


# 1.2 Test : fingerprint stable

from src.data.split import fingerprint_split

def test_split_fingerprint_stable():
    df = pd.DataFrame({
        "geolocation_name": ["A", "B"],
        "quarter_label": ["Q1", "Q2"],
    })

    fp1 = fingerprint_split(
        df,
        id_columns=["geolocation_name", "quarter_label"]
    )
    fp2 = fingerprint_split(
        df.sample(frac=1),  # shuffle
        id_columns=["geolocation_name", "quarter_label"]
    )

    assert fp1 == fp2

    # 1.3 Test : fingerprint change si split change

    def test_split_fingerprint_changes_when_rows_change():
    df1 = pd.DataFrame({
        "geolocation_name": ["A"],
        "quarter_label": ["Q1"],
    })

    df2 = pd.DataFrame({
        "geolocation_name": ["A"],
        "quarter_label": ["Q2"],
    })

    fp1 = fingerprint_split(df1, ["geolocation_name", "quarter_label"])
    fp2 = fingerprint_split(df2, ["geolocation_name", "quarter_label"])

    assert fp1 != fp2
