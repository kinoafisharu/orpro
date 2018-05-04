function viewFormEdit(elem_id) {
    $('#alert-pop-up').html('');
    $('#alert-pop-up').css({'background': 'none'});

    var button_element = document.getElementById(elem_id);
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/edit-ajax-forms/' + button_element.dataset.templateName +
        '?model-id=' + button_element.dataset.modelId, true)
    xhr.send();

    xhr.onreadystatechange = function() {
      if (xhr.readyState != 4) return;

      if (xhr.status != 200) {
        viewPopUpAlert(false, xhr.statusText, xhr.status);
      } else {
        response = xhr.responseText;


        $('#send-form-ajax').html(response);
      }
    }

    // Во время ожидания ответа от сервера, отображается спинер загрузки.
    $('.admin-panel-pop-up').css({'display': 'block'});
    $('body').css({'overflow': 'hidden'});
    $('#send-form-ajax').html('<p class="load-span"><i class="fa fa-spinner fa-spin fa-2x"></i></p>');
}


$(function() {
  // При нажатии на фон формы редактирования, окно закрывается.
  $('.custom-pop-up-blur').click(function() {
    $('.admin-panel-pop-up').css({'display': 'none'});
    $('body').css({'overflow': ''});
  });
})




function sendData() {
  var xhr = new XMLHttpRequest();
  var data = new FormData();
  var formElement = $('#send-form-ajax');
  var csrf = $('[name=csrfmiddlewaretoken]').val()
  var searchParams = new URLSearchParams('csrfmiddlewaretoken='+ csrf +'&'+ formElement.serialize());

  xhr.open('POST', '/edit-ajax-forms/'+ searchParams.get('template-name-edit'), true)
  xhr.send(searchParams);

  xhr.onreadystatechange = function() {
    if (xhr.readyState != 4) return;

    if (xhr.status != 200) {
      viewPopUpAlert(false, xhr.statusText, xhr.status);
    } else {
      viewPopUpAlert(true);
    }
  }
}

function viewPopUpAlert(is_good, response_text=null, status=null) {
  $('#send-form-ajax').html('');


  if (is_good){
    //$('#alert-pop-up').html('<p style="color: #157eb3;">'+ response_text +'</p>');
    $('#alert-pop-up').css({'display': 'block'});
    $('.admin-panel-pop-up').css({'display': 'none'});
    $('body').css({'overflow': ''});
    $('#alert-pop-up').css({'display': 'none'});
    location.reload();
  } else {
    $('#alert-pop-up').css({'background': '#d22e2e'});
    $('#alert-pop-up').html('<p>Status code: '+ status +'</p>\
          <p>Error text: ' + response_text +'</p>');
    $('#alert-pop-up').css({'display': 'block'});
    return;
  }
}
