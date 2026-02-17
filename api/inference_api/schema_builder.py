from pydantic import BaseModel, Field, create_model

def build_pydantic_model(schema_dict):

    fields = {}

    for name, config in schema_dict.items():

        field_type = eval(config["type"])

        fields[name] = (
            field_type,
            Field(... if config["required"] else None)
        )

    return create_model("DynamicInputModel", **fields)
