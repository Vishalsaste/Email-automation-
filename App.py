import streamlit as st
import smtplib
import pandas as pd
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from io import BytesIO

# Page config
st.set_page_config(page_title="Bulk Email Sender", page_icon="📧", layout="centered")

st.title("📧 Bulk Email Sender")
st.markdown("Send personalized bulk emails with placeholders and delay control.")

# --- Login Section ---
with st.container():
    st.subheader("🔐 Login Details")
    col1, col2 = st.columns(2)
    with col1:
        sender_email = st.text_input("Your Email")
        sender_name = st.text_input("Sender Name")
    with col2:
        app_password = st.text_input("App Password", type="password")

# --- Upload Section ---
with st.container():
    st.subheader("📂 Upload Recipient List / Sent Emails Log")
    st.markdown(
        "CSV must contain the following columns: "
        "**email, first_name, last_name**"
    )
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

    df = None
    if uploaded_file is not None:
        try:
            # Check if file is empty
            if uploaded_file.getbuffer().nbytes == 0:
                st.error("❌ Uploaded file is empty. Please upload a valid CSV.")
            else:
                # Reset pointer before reading
                uploaded_file.seek(0)
                
                # Attempt UTF-8 first, fallback to Latin1
                try:
                    df = pd.read_csv(uploaded_file, encoding="utf-8")
                except UnicodeDecodeError:
                    uploaded_file.seek(0)  # reset pointer again
                    df = pd.read_csv(uploaded_file, encoding="latin1")
                
                # Check for required columns
                required_cols = {
                    "email",
                    "first_name",
                    "last_name",
                }
                if not required_cols.issubset(df.columns):
                    st.error(f"❌ CSV must contain columns: {', '.join(required_cols)}")
                    df = None
                else:
                    st.success("✅ CSV loaded successfully!")
                    st.write("📊 Preview of uploaded data (first 5 rows):")
                    st.dataframe(df.head())
        except pd.errors.EmptyDataError:
            st.error("❌ The uploaded file is empty or not a valid CSV.")
        except Exception as e:
            st.error(f"⚠️ Error reading CSV: {str(e)}")

# --- Email Template Section ---
with st.container():
    st.subheader("📝 Email Template")
    subject_template = st.text_input("Subject (use {full_name}, {first_name}, {last_name})")
    body_template = st.text_area(
        "Email Body (use {first_name}, {last_name}, {full_name})",
        height=200,
        placeholder="Dear {first_name},\n\nGreetings! Hope this email finds you well.\n\nYour message here.\n\nRegards,\n{full_name}"
    )

# --- Delay Control ---
with st.container():
    st.subheader("⏳ Sending Options")
    delay = st.slider("Delay between emails (seconds)", min_value=10, max_value=120, value=30, step=5)

# --- Send Button ---
if st.button("🚀 Send Emails"):
    if df is not None and sender_email and app_password:
        try:
            server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
            server.login(sender_email, app_password)

            progress = st.progress(0)
            total = len(df)

            success_count = 0
            fail_count = 0
            failed_emails = []

            for idx, row in df.iterrows():
                recipient = row['email']
                first = row['first_name']
                last = row['last_name']
                full_name = f"{first} {last}"

                # Replace placeholders
                subject = subject_template.format(first_name=first, last_name=last, full_name=full_name)
                body = body_template.format(first_name=first, last_name=last, full_name=full_name)

                # Convert newlines to <br> for HTML formatting
                body_html = body.replace("\n", "<br>")

                msg = MIMEMultipart()
                msg["From"] = f"{sender_name} <{sender_email}>"
                msg["To"] = recipient
                msg["Subject"] = subject
                msg.attach(MIMEText(body_html, "html"))

                try:
                    server.sendmail(sender_email, recipient, msg.as_string())
                    success_count += 1
                except Exception as e:
                    fail_count += 1
                    failed_emails.append({
                        "email": recipient,
                        "first_name": first,
                        "last_name": last,
                        "error": str(e)
                    })

                progress.progress((idx + 1) / total)

                # Delay before sending the next email
                if idx < total - 1:
                    time.sleep(delay)

            server.quit()

            # --- Final Summary ---
            st.success(f"🎉 Process completed!\n\n✅ Sent: {success_count}\n❌ Failed: {fail_count}\n📩 Total: {total}")

            # --- Export failed emails if any ---
            if fail_count > 0:
                failed_df = pd.DataFrame(failed_emails)
                buffer = BytesIO()
                failed_df.to_csv(buffer, index=False)
                buffer.seek(0)

                st.error("Some emails failed. Download the list below:")
                st.download_button(
                    label="⬇️ Download Failed Emails CSV",
                    data=buffer,
                    file_name="failed_emails.csv",
                    mime="text/csv"
                )

        except Exception as e:
            st.error(f"⚠️ Error sending emails: {str(e)}")
    else:
        st.warning("⚠️ Please provide login details and upload a valid CSV.")
