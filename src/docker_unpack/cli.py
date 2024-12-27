from watcloud_utils.typer import app

@app.command()
def unpack():
    print("Unpacking the docker image")
