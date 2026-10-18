from nema_agora.spectral_indices import calculate_msavi2,expanded_spectral_evidence
def test_msavi2_expected(): assert round(calculate_msavi2(red=.2,nir=.8),6)==round((2*.8+1-(((2*.8+1)**2-8*(.8-.2))**.5))/2,6)
def test_expanded_indices(): x=expanded_spectral_evidence(scene_id="S73",band_values={"B03":.6,"B04":.2,"B08":.8});assert x["state"]=="VALID";assert set(x["index_values"])=={"NDVI","NDWI_MCFEETERS","MSAVI2"}
def test_invalid_reflectance_fails(): assert expanded_spectral_evidence(scene_id="S73",band_values={"B03":.6,"B04":1.2,"B08":.8})["state"]=="CONTROL_REQUIRED"
def test_deterministic(): b={"B03":.6,"B04":.2,"B08":.8};assert expanded_spectral_evidence(scene_id="S73",band_values=b)["fingerprint"]==expanded_spectral_evidence(scene_id="S73",band_values=b)["fingerprint"]