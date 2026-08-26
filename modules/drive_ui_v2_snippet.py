# Replaces the "with n_tabs[0]:" Drive block inside render_nexus_vault().

import drive_v2
from classification import LEVELS, clearance_for_user

with n_tabs[0]:
    st.markdown("### ðŸ“ Nexus Drive â€” Cloud Storage & Vault")

    requester_clearance = clearance_for_user(is_admin=is_admin())

    quota = drive_v2.get_quota_status(user_email)
    st.progress(min(quota.percent_used / 100, 1.0))
    st.caption(
        f"{quota.used_bytes / (1024*1024):.1f} MB used of "
        f"{quota.limit_bytes / (1024*1024*1024):.1f} GB "
        f"({quota.percent_used:.1f}%) â€” "
        + ("âœ… cloud storage active" if drive_v2.is_s3_configured() else "âš ï¸ local fallback (not durable â€” configure S3_* for real cloud storage)")
    )

    uploaded = st.file_uploader("Upload file to cloud storage", key="nexus_drive_up_v2")
    c_cat = st.selectbox("File Category", ["Documents", "Research Data", "Media", "Backups"], key="drive_cat_v2")
    c_classification = st.selectbox("Classification", LEVELS, index=1, key="drive_classification_v2",
                                     help="Who can see this file: PUBLIC (everyone), INTERNAL (default, most users), CONFIDENTIAL, RESTRICTED (admins only).")
    c_notes = st.text_input("File Description / Notes", key="drive_notes_v2")

    if uploaded:
        try:
            result = drive_v2.store_file(uploaded.name, uploaded.getvalue(), c_cat, c_notes, user_email, classification=c_classification)
            st.success(f"âœ… Uploaded **{uploaded.name}** ({result['backend']}, classified {result['classification']}).")
        except drive_v2.QuotaExceeded as e:
            st.error(f"âŒ Upload rejected â€” over quota. {e}")

    files = drive_v2.list_files(user_email, requester_clearance)
    if files:
        import pandas as pd
        df_files = pd.DataFrame(files)
        st.dataframe(df_files, width='stretch', hide_index=True)

        del_id = st.number_input("Enter File ID to Delete", min_value=0, step=1, key="del_file_id_v2")
        dl_id = st.number_input("Enter File ID to Download", min_value=0, step=1, key="dl_file_id_v2")

        col_del, col_dl = st.columns(2)
        with col_del:
            if st.button("ðŸ—‘ï¸ Delete Selected File"):
                try:
                    drive_v2.delete_file(int(del_id), user_email, requester_clearance)
                    st.success("âœ… File removed.")
                    st.rerun()
                except drive_v2.AccessDenied as e:
                    st.error(f"âŒ {e.reason}")
                except ValueError as e:
                    st.error(f"âŒ {e}")
        with col_dl:
            if st.button("â¬‡ï¸ Get Download Link"):
                try:
                    dl = drive_v2.get_download(int(dl_id), user_email, requester_clearance)
                    if dl["method"] == "presigned_url":
                        st.success(f"Link (expires in {dl['expires_in_seconds']}s): {dl['url']}")
                    else:
                        st.warning(dl["note"])
                except drive_v2.AccessDenied as e:
                    st.error(f"âŒ Access denied: {e.reason}")
                except ValueError as e:
                    st.error(f"âŒ {e}")
    else:
        st.info("Your Drive is empty (or nothing at your clearance level has been shared here yet).")
