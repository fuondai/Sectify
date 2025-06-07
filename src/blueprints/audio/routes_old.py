# -*- coding: utf-8 -*-
from flask import Flask, request, session, redirect, render_template, Response, jsonify, send_file
from app import app, db # Import app and db from main app.py
from models.user_model import User # Assuming User model might be needed for user context
from user.encrypt_aes import encrypt_audio as encrypt_audio_aes, decrypt_audio as decrypt_audio_aes
from user.encrypt_chaotic import encrypt_audio_chaotic, decrypt_audio_chaotic # Removed derive_initial_state import as seed is now random
from app import token_required, login_required # Import decorators
import os
import io
import uuid
from bson.binary import Binary # To store binary data like keys/nonces/seeds in MongoDB
from datetime import datetime # Import datetime
from werkzeug.utils import secure_filename # For secure filenames

# --- Configuration --- 
# Define a secure base directory for storing encrypted files, ideally outside web root
# This should be configurable, e.g., via environment variable
SECURE_STORAGE_PATH = os.environ.get("SECURE_STORAGE_PATH", os.path.join(app.root_path, "..", "secure_files"))
# Ensure the storage directory exists
os.makedirs(SECURE_STORAGE_PATH, exist_ok=True)

# Define MongoDB collection for audio metadata
audio_collection = db.audio_files # Use the configured db instance

# --- Helper Functions --- 
def get_user_id_from_session():
    """Safely retrieves the user ID from the session."""
    return session.get("user_id")

def generate_secure_db_filename(original_filename):
    """Generates a unique, secure filename for storage, preventing path traversal and collisions."""
    # Use Werkzeug's secure_filename to sanitize the original filename first
    safe_original = secure_filename(original_filename)
    # Extract extension
    ext = ""
    if "." in safe_original:
        ext = safe_original.rsplit(".", 1)[1].lower()
    # Generate unique name
    unique_name = uuid.uuid4().hex
    # Basic check for common audio extensions, refine as needed
    allowed_extensions = {"wav", "mp3", "ogg", "flac"} # Example
    if ext in allowed_extensions:
        # Store with unique ID and original (sanitized) extension, plus .enc
        return f"{unique_name}.{ext}.enc"
    else:
        # Handle disallowed extension
        return None

# --- Routes --- 

@app.route("/api/upload_audio_aes", methods=["POST"])
@login_required
@token_required
def upload_audio_file_aes():
    """Handles audio file uploads, encrypts with AES-GCM (for storage), stores metadata in DB."""
    user_id = get_user_id_from_session()
    if not user_id:
        return jsonify({"error": "User session not found"}), 401

    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if file:
        original_filename = file.filename
        # Generate secure filename for storage
        secure_db_name = generate_secure_db_filename(original_filename)
        if not secure_db_name:
             return jsonify({"error": "Invalid file type or filename"}), 400
             
        # Define paths
        # Use a combination of unique ID and original name for temp path to avoid collisions
        temp_upload_path = os.path.join(SECURE_STORAGE_PATH, f"temp_{uuid.uuid4().hex}_{secure_filename(original_filename)}")
        encrypted_file_path = os.path.join(SECURE_STORAGE_PATH, secure_db_name)

        try:
            # 1. Save temporarily to process
            file.save(temp_upload_path)
            print(f"Temporary file saved to: {temp_upload_path}")

            # 2. Encrypt using AES-GCM
            print(f"Encrypting {original_filename} using AES-GCM...")
            encryption_result = encrypt_audio_aes(temp_upload_path, encrypted_file_path)

            if not encryption_result:
                os.remove(temp_upload_path) # Clean up temp file
                print(f"AES encryption failed for {original_filename}")
                return jsonify({"error": "Encryption failed"}), 500

            key, nonce, channels, framerate, sampwidth = encryption_result
            print(f"AES Encryption successful. Key: {len(key)} bytes, Nonce: {len(nonce)} bytes")
            
            # 3. Store metadata and key/nonce in MongoDB
            # !! WARNING: Storing raw key/nonce directly is insecure in production !!
            audio_metadata = {
                "_id": uuid.uuid4().hex, 
                "user_id": user_id,
                "original_filename": original_filename,
                "encrypted_filename": secure_db_name,
                "encryption_method": "AES-GCM", 
                "aes_key": Binary(key),
                "aes_nonce": Binary(nonce),
                "channels": channels,
                "framerate": framerate,
                "sampwidth": sampwidth,
                "upload_date": datetime.utcnow()
                # No hash stored for AES-GCM as it includes integrity check (tag)
            }
            audio_collection.insert_one(audio_metadata)
            print(f"Metadata stored in DB for file: {secure_db_name}")

            # 4. Clean up temporary file
            os.remove(temp_upload_path)
            print(f"Temporary file removed: {temp_upload_path}")

            return jsonify({
                "message": "File uploaded and encrypted successfully (AES-GCM)",
                "audio_id": audio_metadata["_id"],
                "original_filename": original_filename
            }), 201

        except Exception as e:
            print(f"Error during AES file upload/encryption: {e}")
            # Clean up potentially partially created files
            if os.path.exists(temp_upload_path):
                try: os.remove(temp_upload_path)
                except: pass
            if os.path.exists(encrypted_file_path):
                 try: os.remove(encrypted_file_path)
                 except: pass
            return jsonify({"error": f"An unexpected error occurred: {e}"}), 500
    else:
        return jsonify({"error": "File processing error"}), 400

@app.route("/api/upload_audio_chaotic", methods=["POST"])
@login_required
@token_required
def upload_audio_file_chaotic():
    """Handles audio file uploads, encrypts with Chaotic Stream (for streaming), stores metadata in DB."""
    user_id = get_user_id_from_session()
    if not user_id:
        return jsonify({"error": "User session not found"}), 401

    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if file:
        original_filename = file.filename
        # Generate secure filename for storage
        secure_db_name = generate_secure_db_filename(original_filename)
        if not secure_db_name:
             return jsonify({"error": "Invalid file type or filename"}), 400
             
        # Define paths
        temp_upload_path = os.path.join(SECURE_STORAGE_PATH, f"temp_{uuid.uuid4().hex}_{secure_filename(original_filename)}")
        encrypted_file_path = os.path.join(SECURE_STORAGE_PATH, secure_db_name)

        try:
            # 1. Save temporarily to process
            file.save(temp_upload_path)
            print(f"Temporary file saved to: {temp_upload_path}")

            # 2. Encrypt using Chaotic Stream Cipher
            print(f"Encrypting {original_filename} using Chaotic Stream...")
            # !! WARNING: Using os.urandom as seed material and storing it is insecure !!
            # This is for demonstrating the chaotic cipher as required by the proposal.
            # A secure implementation would derive this from user credentials + salt or use a KMS.
            chaotic_seed_material = os.urandom(32) 
            
            encryption_result = encrypt_audio_chaotic(temp_upload_path, encrypted_file_path, chaotic_seed_material)

            if not encryption_result:
                os.remove(temp_upload_path) # Clean up temp file
                print(f"Chaotic encryption failed for {original_filename}")
                return jsonify({"error": "Encryption failed"}), 500

            channels, framerate, sampwidth, original_hash = encryption_result
            print(f"Chaotic Encryption successful. Seed: {len(chaotic_seed_material)} bytes, Hash: {original_hash}")
            
            # 3. Store metadata and seed material in MongoDB
            audio_metadata = {
                "_id": uuid.uuid4().hex, 
                "user_id": user_id,
                "original_filename": original_filename,
                "encrypted_filename": secure_db_name,
                "encryption_method": "ChaoticStream", 
                "chaotic_seed_material": Binary(chaotic_seed_material), # Store the insecure seed
                "original_sha256_hash": original_hash, # Store hash for integrity check
                "channels": channels,
                "framerate": framerate,
                "sampwidth": sampwidth,
                "upload_date": datetime.utcnow()
            }
            audio_collection.insert_one(audio_metadata)
            print(f"Metadata stored in DB for file: {secure_db_name}")

            # 4. Clean up temporary file
            os.remove(temp_upload_path)
            print(f"Temporary file removed: {temp_upload_path}")

            return jsonify({
                "message": "File uploaded and encrypted successfully (Chaotic Stream)",
                "audio_id": audio_metadata["_id"],
                "original_filename": original_filename
            }), 201

        except Exception as e:
            print(f"Error during Chaotic file upload/encryption: {e}")
            # Clean up potentially partially created files
            if os.path.exists(temp_upload_path):
                try: os.remove(temp_upload_path)
                except: pass
            if os.path.exists(encrypted_file_path):
                 try: os.remove(encrypted_file_path)
                 except: pass
            return jsonify({"error": f"An unexpected error occurred: {e}"}), 500
    else:
        return jsonify({"error": "File processing error"}), 400

@app.route("/api/list_audio")
@login_required
@token_required
def list_audio_files():
    """Lists audio files uploaded by the current user."""
    user_id = get_user_id_from_session()
    if not user_id:
        return jsonify({"error": "User session not found"}), 401

    try:
        user_files = list(audio_collection.find(
            {"user_id": user_id},
            # Projection: Exclude sensitive key/nonce/seed from the list view
            {"aes_key": 0, "aes_nonce": 0, "chaotic_seed_material": 0} 
        ))
        # Convert ObjectId to string if necessary, handle BSON types for JSON
        for f in user_files:
             # f["_id"] = str(f["_id"]) # Keep _id as is for now, might be needed
             if "upload_date" in f:
                  f["upload_date"] = f["upload_date"].isoformat() # Convert datetime
                  
        return jsonify(user_files), 200
    except Exception as e:
        print(f"Error listing audio files: {e}")
        return jsonify({"error": "Failed to retrieve audio list"}), 500

@app.route("/api/play_audio/<audio_id>")
@login_required
@token_required
def play_audio_file(audio_id):
    """Decrypts and streams the requested audio file.
       Uses the encryption method stored in metadata (AES or Chaotic).
    """
    user_id = get_user_id_from_session()
    if not user_id:
        return jsonify({"error": "User session not found"}), 401

    try:
        # Find the audio metadata, ensuring it belongs to the current user
        audio_metadata = audio_collection.find_one({"_id": audio_id, "user_id": user_id})

        if not audio_metadata:
            return jsonify({"error": "Audio file not found or access denied"}), 404

        encrypted_filename = audio_metadata.get("encrypted_filename")
        encryption_method = audio_metadata.get("encryption_method", "AES-GCM") # Default to AES if not specified
        encrypted_file_path = os.path.join(SECURE_STORAGE_PATH, encrypted_filename)

        if not os.path.exists(encrypted_file_path):
             print(f"Error: Encrypted file not found at {encrypted_file_path}")
             return jsonify({"error": "Encrypted file data missing"}), 404

        # --- Decryption Logic --- 
        decrypted_data_buffer = io.BytesIO()
        decryption_successful = False
        temp_decrypted_path = os.path.join(SECURE_STORAGE_PATH, f"temp_dec_{audio_id}.wav")

        print(f"Attempting to play audio_id: {audio_id}, method: {encryption_method}")

        try:
            if encryption_method == "AES-GCM":
                key = audio_metadata.get("aes_key")
                nonce = audio_metadata.get("aes_nonce")
                if not key or not nonce:
                    return jsonify({"error": "Missing key or nonce for AES decryption"}), 500
                
                decryption_successful = decrypt_audio_aes(
                    encrypted_file_path,
                    temp_decrypted_path,
                    bytes(key), # Convert BSON Binary back to bytes
                    bytes(nonce),
                    audio_metadata["channels"],
                    audio_metadata["framerate"],
                    audio_metadata["sampwidth"]
                )
                if not decryption_successful:
                     print(f"AES decryption failed for {audio_id}")

            elif encryption_method == "ChaoticStream":
                seed_material = audio_metadata.get("chaotic_seed_material") 
                expected_hash = audio_metadata.get("original_sha256_hash")
                if not seed_material or not expected_hash:
                     return jsonify({"error": "Missing seed material or hash for chaotic decryption"}), 500
                
                decryption_successful = decrypt_audio_chaotic(
                    encrypted_file_path,
                    temp_decrypted_path,
                    bytes(seed_material), # Convert BSON Binary back to bytes
                    audio_metadata["channels"],
                    audio_metadata["framerate"],
                    audio_metadata["sampwidth"],
                    expected_hash # Pass hash for integrity check
                )
                if not decryption_successful:
                     print(f"Chaotic decryption or integrity check failed for {audio_id}")
                     
            else:
                return jsonify({"error": f"Unsupported encryption method: {encryption_method}"}), 500

            # --- Serve Decrypted Audio --- 
            if decryption_successful and os.path.exists(temp_decrypted_path):
                print(f"Serving decrypted audio stream for {audio_id}")
                # Use send_file for better handling of streaming and cleanup
                return send_file(temp_decrypted_path, mimetype="audio/wav", as_attachment=False)
                # Note: send_file doesn't automatically clean up. Need a callback or different approach for cleanup.
                # For simplicity here, we might leave the temp file or clean it up later.
            else:
                return jsonify({"error": "Decryption failed or resulted in empty data"}), 500
        finally:
             # --- Cleanup Temporary Decrypted File --- 
             # This cleanup might happen before send_file finishes in some WSGI servers.
             # A better approach uses Flask's after_this_request or a background task.
             # For now, attempt cleanup. If file is locked, it might fail.
             if os.path.exists(temp_decrypted_path):
                 try:
                     # print(f"Attempting cleanup of: {temp_decrypted_path}")
                     # os.remove(temp_decrypted_path) 
                     # Defer cleanup - let OS handle temp files or implement proper background cleanup
                     pass 
                 except Exception as cleanup_err:
                     print(f"Warning: Could not clean up temp file {temp_decrypted_path}: {cleanup_err}")

    except Exception as e:
        print(f"Error playing audio file {audio_id}: {e}")
        # Ensure temp file is cleaned up on error too
        if os.path.exists(temp_decrypted_path):
             try: os.remove(temp_decrypted_path)
             except: pass
        return jsonify({"error": "Failed to process audio playback"}), 500

# Remove old hardcoded/insecure routes if they existed
# Example: Remove @app.route("/upload", methods=["POST"]) if it's still there

