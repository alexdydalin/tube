var button = document.getElementById("eye");
button.onclick = show;
var input = document.getElementById("password");
var icon = document.getElementById("eye");

function show () {
    if(input.getAttribute('type') === 'password') {
        input.removeAttribute('type');
        input.setAttribute('type', 'text');
        icon.className = 'far fa-eye';
    } else {
        input.removeAttribute('type');
        input.setAttribute('type', 'password');
        icon.className = '' + 'far fa-eye-slash';
    }
}
