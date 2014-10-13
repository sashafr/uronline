var textbox = document.getElementById('searchbar');
var dropdown = document.getElementById('properties_dropdown');

dropdown.onchange = function(){
     textbox.value = textbox.value + this.value;
}