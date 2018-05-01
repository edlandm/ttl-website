// Utility functions used sitewide
function addClass(el, className) {
    // Add a css clas to an element (el)
    // Returns el
    if(el.classList)
        el.classList.add(className);
    else
        el.className += ' ' + className;
    return el;
}
function removeClass(el, className) {
    // Remove a css class from an element (el)
    // Returns el
    if(el.classList)
        el.classList.remove(className);
    else {
        el.className = el.className.replace(
            new RegExp('(^|\\b)' + className.split(' ').join('|') + '(\\b|$)', 'gi'), ' ');
    }
    return el;
}
function toggleClass(el, className) {
    // Toggle the className of an element (el)
    // Returns el
    if(el.classList) {
        el.classList.toggle(className);
    } else {
        var classes = el.className.split(' '),
            existingIndex = classes.indexOf(className);

        if(existingIndex >= 0)
        classes.splice(existingIndex, 1);
        else
        classes.push(className);

        el.className = classes.join(' ');
    }
    return el;
};
function post(path, params, method) {
    // send post request
    method = method || "post"; // Set method to post by default if not specified.

    // The rest of this code assumes you are not using a library.
    // It can be made less wordy if you use one.
    var form = document.createElement("form");
    form.setAttribute("method", method);
    form.setAttribute("action", path);

    for(var key in params) {
        if(params.hasOwnProperty(key)) {
            var hiddenField = document.createElement("input");
            hiddenField.setAttribute("type", "hidden");
            hiddenField.setAttribute("name", key);
            hiddenField.setAttribute("value", params[key]);

            form.appendChild(hiddenField);
        }
    }

    document.body.appendChild(form);
    form.submit();
};
function postJSON(path, data, token, callback, method) {
    // send json data as post request
    method = method || "post"; // Set method to post by default if not specified.
    var xhr = new XMLHttpRequest();

    xhr.open(method, path, true);
    xhr.setRequestHeader('Content-Type', 'application/json; charset=UTF-8');
    xhr.setRequestHeader('X-CSRFToken', token);
    xhr.send(JSON.stringify(data));

    if(callback) {
        xhr.onloadend = callback;
    }
};
function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
            newElement = document.createElement("div");
            newElement.classList.add(className);
            newElement.innerHTML = message;
            el.appendChild(newElement);
            break;
        case "before":
            htmlString = '<div class="' + className + '">' + message + '</div>';
            el.insertAdjacentHTML("beforebegin", htmlString);
            break;
        case "prepend":
            newElement = document.createElement("div");
            newElement.classList.add(className);
            newElement.innerHTML = message
            el.insertBefore(newElement, el.parent.firstChild);
            break;
        default:
            console.log("Invalid position given");
            return false;
    }
    return true;
}
function deleteByClassName(className) {
    // remove all elements with class='<className>' from the DOM
    var els = document.getElementsByClassName(className);
    while(els.length > 0) {
        els[0].parentNode.removeChild(els[0]);
    }
}
function clearErrors() {
    // remove all error messages (className="error")
    var errors = document.getElementsByClassName("error");
    while(errors.length > 0) {
        errors[0].parentNode.removeChild(errors[0]);
    }
}

forEach = Array.prototype.forEach.call.bind(Array.prototype.forEach);

// I found this function from:
// http://unscriptable.com/2009/03/20/debouncing-javascript-methods/
var debounce = function (func, threshold, execAsap) {
    //  Returns a function that is only excecuted once during threshold
    var timeout;
    return function debounced () {
        var obj = this, args = arguments;
        function delayed () {
            if (!execAsap)
                func.apply(obj, args);
            timeout = null;
        };

        if (timeout)
            clearTimeout(timeout);
        else if (execAsap)
            func.apply(obj, args);

        timeout = setTimeout(delayed, threshold || 100);
    };
}
