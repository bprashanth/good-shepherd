import ee

def verify_gee_access():
    """
    Pings GEE asset metadata to confirm read access.
    """
    try:
        ee.Initialize()
        print("Earth Engine Initialized Successfully.\n")
    except Exception as e:
        print(f"Failed to initialize EE: {e}")
        return

    # The exact assets needed for your Phase 1 Delta and Cover analysis
    assets_to_test = {
        # Your confirmed 2019 regional height map
        "Potapov_Height_2019_SASIA": "users/potapovpeter/GEDI_V27/GEDI_SASIA_v27",
        
        # The official 2000 global height baselines (Often IAM restricted)
        "Potapov_Height_2000_v1": "UMD/GLAD/GlobalForestHeight/v1/2000",
        "Potapov_Height_2000_v2": "projects/glad/GLCLU2020/Forest_height_2000",
        "Potapov_Height_2000_v22": "projects/glad/GLCLU2022/v2/Forest_height_2000",
        
        # The public 2000 cover baseline (Hansen Global Forest Change)
        "Hansen_Cover_2000": "UMD/hansen/global_forest_change_2023_v1_11"
    }

    print("--- Asset Access Verification ---")
    for name, path in assets_to_test.items():
        try:
            # getAsset returns metadata if accessible, throws an HttpError if not
            info = ee.data.getAsset(path)
            asset_type = info.get('type', 'Unknown')
            print(f"✅ SUCCESS | {name}")
            print(f"   -> Type: {asset_type}")
            print(f"   -> Path: {path}\n")
        except Exception as e:
            # Clean up the ugly HttpError string for readability
            error_str = str(e)
            if 'returned "' in error_str:
                clean_error = error_str.split('returned "')[-1].split('". Details:')[0]
            else:
                clean_error = error_str.split('Details: ')[-1] if 'Details: ' in error_str else error_str
            
            print(f"❌ FAILED  | {name}")
            print(f"   -> Reason: {clean_error}")
            print(f"   -> Path: {path}\n")

if __name__ == "__main__":
    verify_gee_access()
