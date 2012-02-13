
debug_response = function(json) {
  var message = JSON.parse(json);
  console.log(message);
}

sendAjaxJsonMessage = function(path, opt_object, opt_callback, opt_this) {
  $.ajax({
      url: path,
      type: 'POST',
      data: opt_object,
      success: function(data) {
        opt_callback.call(opt_this, data);
      }
  });
};

Controller = function() {
  this.history = [];
  this.cur_history = -1;
  this.history_has_unevaled = false;
};

Controller.prototype.send_input = function() {
  this.input = this.input_codemirror.getValue();
  this.input_codemirror.setValue('');
  var message = {};
  message.input = this.input;
  sendAjaxJsonMessage('/input_new', message, this.ack, this);
  console.log('sending', message);
};

Controller.prototype.ack = function(message) {
  if (message.status == 'ok') {
    this.extend_output(this.input);
    this.update_history(this.input);
    this.input = '';
  } else {
    alert(message.status);
    this.undo();
  }
};


Controller.prototype.extend_output = function(message) {
  this.output_codemirror.setValue(
    this.output_codemirror.getValue() + '\n' + message);
  this.output_codemirror.setCursor(this.output_codemirror.lineCount());
}

Controller.prototype.message_received = function(message) {
  console.log(message);
  this.extend_output(message.newoutput);
}

Controller.prototype.undo = function() {
  this.input_codemirror.setValue(this.input);
  this.input = '';
};

Controller.prototype.up_arrow = function(message) {
  if (this.cur_history < 0) return;
  if (!this.history_has_unevaled) {
    this.history.push(this.input_codemirror.getValue());
    this.history_has_unevaled = true;
  }
  this.input_codemirror.setValue(this.history[this.cur_history]);
  this.cur_history -= 1;
}

Controller.prototype.update_history = function(text) {
  if (this.history_has_unevaled) this.history.pop();
  this.history.push(text);
  this.history_has_unevaled = false;
  this.cur_history = this.history.length - 1;
}

Controller.prototype.down_arrow = function(message) {
  if (this.cur_history + 2 >= this.history.length) return;
  this.input_codemirror.setValue(this.history[this.cur_history + 2]);
  if (this.cur_history + 2 >= this.history.length - 1
      && this.history_has_unevaled) {
    this.history_has_unevaled = false;
    this.history.pop();
  }
  this.cur_history += 1;
}

establishChannel = function(token) {
  if (token === undefined) {
    $.ajax({
        url: '/get_channel_token',
        type: 'POST',
        success: function(token) {
          establishChannel(token);
        }
    });
    return;
  }
  var onMessage = function(messageObject) {
    var message = JSON.parse(messageObject.data);
    controller.message_received(message);
  }
  var onOpened = function() {
    console.log('channel established');
  }
  var onError = function(error) {
    console.log('channel error', error);
    establishChannel();
  }
  var onClose = function() {
    console.log('channel closed');
    establishChannel();
  }
  var channel = new goog.appengine.Channel(token);
  var socket = channel.open();
  socket.onopen = onOpened;
  socket.onmessage = onMessage;
  socket.onerror = onError;
  socket.onclose = onClose;
}

onload = function() {
  controller = new Controller();

  var output = CodeMirror.fromTextArea(document.getElementById("output2"), {
    lineNumbers: true,
    readOnly: true,
  });
  output.setCursor(output.lineCount());

  var input = CodeMirror.fromTextArea(document.getElementById("input2"), {
    lineNumbers: false,
    indentUnit: 4,
    onKeyEvent:
      function(editor, e) {
          if (e.keyCode === 13 && e.type === 'keydown' && e.shiftKey) {
              controller.send_input();
              e.stop();
              return true;
          }
          if (e.keyCode === 13 && e.type === 'keyup' && e.shiftKey) {
              e.stop();
              return true;
          }
          if (e.keyCode === 40 && e.type === 'keydown' &&
              editor.getCursor().line === editor.lineCount() - 1) {
              controller.down_arrow();
              e.stop();
              return true;
          }
          if (e.keyCode === 38 && e.type === 'keydown' &&
              editor.getCursor().line === 0) {
              controller.up_arrow();
              e.stop();
              return true;
          }
      }
  });
  controller.input_codemirror = input;
  controller.output_codemirror = output;

  establishChannel(token);
  
  $('#wrap-btn').click(function() {
    var wrapping = output.getOption('lineWrapping');
    output.setOption('lineWrapping', !wrapping);
  });
}

document.addEventListener('onload', onload);
