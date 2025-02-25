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


// Maybe this could be more elegant with react if you wanna change it idm
    // Table popup


    });


document.addEventListener("DOMContentLoaded",function(){
    function formatTeamName(teamName) {
        return teamName.toLowerCase().replace(/\s/g, "_") + ".png";
    }
    document.querySelectorAll("[data-team]").forEach(teamElement =>{
        let teamName = teamElement.dataset.team.trim();
        let crestImg = teamElement

        if(teamName){
            let crestPath = `/static/${formatTeamName(teamName)}`;
            crestImg.src = crestPath; 
        }

    });
});
