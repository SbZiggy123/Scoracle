document.addEventListener("DOMContentLoaded", function(){
    var dropdown = document.querySelector('.dropdown')

    dropdown.addEventListener('click', function(){
        showDropdown();
    })

    dropdown.addEventListener('mouseover', function(){
        showDropdown();
    })

    dropdown.addEventListener('mouseleave', function(){
        hideDropdown();
    })

    function showDropdown(){
        var content = dropdown.querySelector('.Content')
        content.classList.toggle('show')
    }

    function hideDropdown(){
        var content = dropdown.querySelector('.Content')
        content.classList.remove('show')
    }
})