def get_eln_connector(eln_type: str = "cheminfo"):
    if eln_type == "cheminfo":
        from .cheminfo import CheminfoElnConnector
        return CheminfoElnConnector
    elif eln_type == "openbis":
        from .openbis import OpenbisElnConnector
        return OpenbisElnConnector
    else:
        raise Exception(f"The selected ELN connector type ({eln_type}) is not known.")
