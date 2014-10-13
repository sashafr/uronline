""" Utility functions for the base application """

from base.models import GlobalVars

def load_globals():
    """ Returns a dictionary of globals for this app """

    globals = GlobalVars.objects.all()

    global_dict = {}
	
    for global_var in globals:
        global_dict[global_var.variable] = global_var.val
		
    return global_dict