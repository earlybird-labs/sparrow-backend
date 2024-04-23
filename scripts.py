def copy_env_to_example():
    """
    Copies the contents of the .env file to the .env.example file,
    but removes any values after the '=' character, leaving only the keys.
    It also skips empty lines and comments, and avoids transferring lines that only contain '='.
    """
    try:
        with open(".env", "r") as env_file:
            lines = env_file.readlines()

        with open(".env.example", "w") as example_file:
            for line in lines:
                # Skip empty lines and comments
                if line.strip() == "":
                    example_file.write("\n")
                    continue
                if line.strip().startswith("#"):
                    example_file.write(line)
                    continue
                # Split the line at the first '=' and write back only the key part with '='
                key_part = line.split("=")[0].strip()
                if key_part:  # Ensure the key part is not empty
                    example_file.write(key_part + "=\n")

        print("Successfully copied .env to .env.example with keys only.")
    except Exception as e:
        print(f"Failed to copy .env to .env.example: {e}")


# Call the function to perform the operation
copy_env_to_example()
