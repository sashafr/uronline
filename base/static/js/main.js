/*
Resets all the form fields in the public advanced search page to 
default values.
*/
function clear_pub_search() {
    document.getElementById('id_property').selectedIndex = 0;
    document.getElementById('id_search_type').selectedIndex = 0;
    document.getElementById('id_q').value = '';
    document.getElementById('id_op').selectedIndex = 0;    
    document.getElementById('id_property2').selectedIndex = 0;
    document.getElementById('id_search_type2').selectedIndex = 0;
    document.getElementById('id_q2').value = '';
    document.getElementById('id_op2').selectedIndex = 0;    
    document.getElementById('id_property3').selectedIndex = 0;
    document.getElementById('id_search_type3').selectedIndex = 0;
    document.getElementById('id_q3').value = '';
    document.getElementById('id_models_0').checked = false;
    document.getElementById('id_models_1').checked = false;
    document.getElementById('id_models_2').checked = false;
    document.getElementById('id_models_3').checked = false;
    document.getElementById('id_unum').value = '';
    document.getElementById('id_museum_num').value = '';
    document.getElementById('id_object_type').selectedIndex = 0;
    document.getElementById('id_keyword').value = '';
    document.getElementById('id_museum').selectedIndex = 0;
    document.getElementById('id_material').selectedIndex = 0;
}