import { html, PolymerElement } from "../../node_modules/@polymer/polymer/polymer-element.js";
import '../otree-constants/otree-constants.js';
var socket = null;
var listeners = [];
/*

`<redwood-events>` is the lowest-level component. It maintains a single
WebSocket connection to the oTree server, reconnecting if possible. The socket
is a singleton - if you put multiple `<redwood-events>` on a single page there
will still only be one socket opened.

`<redwood-events>` has some facilities for displaying connection status and
ping if the `oTree._debug` variable is set in the oTree constants.

https://otree-redwood.readthedocs.io/webcomponents.html

*/

class RedwoodEvents extends PolymerElement {
  static get properties() {
    return {
      /**
       * ping is useful for testing latency and can be turned on/off
       * with `togglePing()`
       */
      ping: {
        type: Boolean,
        value: false
      },
      _master: {
        type: Boolean,
        value: false
      },
      _sendTime: {
        type: Object,
        value: 0
      },
      _roundTripTimes: {
        type: Array,
        value: () => {
          return [];
        }
      },
      _avgPingTime: {
        type: Number,
        computed: '_computeAvgPingTime(_roundTripTimes.*)'
      },
      _connectionStatus: {
        type: String,
        computed: '_computeConnectionStatus(socket.*, _roundTripTimes.*)'
      },

      /* Bound by the otree-constants component */
      _debug: {
        type: Boolean
        /**
         * Fired when a message is received on the WebSocket.
         *	 
         * @event event
         * @param {event} otree_redwood.models.Event.message
         */

      }
    };
  }

  static get template() {
    return html`
            <otree-constants id="constants" _debug="{{ _debug }}"></otree-constants>
            <template is="dom-if" if="[[ _master ]]">
                <template is="dom-if" if="[[ _debug ]]">
                    <div class="well">
                        <p>Connected: [[ _connectionStatus ]]</p>
                        <p>Ping: [[ _avgPingTime ]]</p>
                        <button type="button" on-click="togglePing" hidden$="[[ ping ]]">Start</button>
                        <button type="button" on-click="togglePing" hidden$="[[ !ping ]]">Stop</button>
                    </div>
                </template>
            </template>
        `;
  }

  ready() {
    super.ready();

    if (socket === null) {
      this._master = true;
      let protocol = 'ws://';

      if (window.location.protocol === 'https:') {
        protocol = 'wss://';
      }

      const addr = protocol + window.location.host + '/redwood' + '/app-name/' + this.$.constants.appName + '/group/' + this.$.constants.group.pk + '/participant/' + this.$.constants.participantCode + '/';
      socket = new ReconnectingWebSocket(addr, null, {
        timeoutInterval: 10000
      });
      socket.onerror = this._onError.bind(this);
      socket.onopen = this._onOpen.bind(this);
      socket.onmessage = this._onMessage.bind(this);
      socket.onclose = this._onClose.bind(this);
    }

    this.socket = socket;
    this.pending = [];
    listeners.push(this);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    listeners.splice(listeners.indexOf(this), 1);
  }

  _onOpen() {
    this.socket = socket;
    listeners.forEach(l => {
      l.pending.forEach(msg => {
        socket.send(msg);
      });
    });

    if (this._debug) {
      this._sendPing();
    }
  }

  _onClose() {
    this.socket = socket;
  }

  _onError(err) {
    this.socket = socket;
    console.error(err);
  }

  _onMessage(message) {
    this.socket = socket;
    const event = JSON.parse(message.data);

    if (event.channel == 'ping') {
      const rtt = Date.now() - event.timestamp;
      this.push('_roundTripTimes', rtt);

      if (this._roundTripTimes.length > 10) {
        this.splice('_roundTripTimes', 0, 1);
      }

      return;
    }

    listeners.forEach(l => {
      l.dispatchEvent(new CustomEvent('event', {
        detail: event
      }));
    });
  }
  /**
   * Toggle `ping` on/off.
   */


  togglePing() {
    this.ping = !this.ping;

    if (this.ping) {
      this._sendPing();
    }
  }

  _sendPing() {
    this.socket = socket;

    if (socket.readyState == 1) {
      socket.send(JSON.stringify({
        'channel': 'ping',
        'timestamp': Date.now(),
        'avgping_time': this._avgPingTime
      }));
    }

    if (this.ping) {
      window.setTimeout(this._sendPing.bind(this), 1000);
    }
  }

  _computeAvgPingTime() {
    if (this._roundTripTimes.length == 0) {
      return NaN;
    }

    const sum = this._roundTripTimes.reduce((acc, val) => {
      return acc + val;
    }, 0);

    return Math.floor(sum / this._roundTripTimes.length);
  }

  _computeConnectionStatus() {
    if (!this.socket) return;

    if (this.socket.readyState == 1) {
      return 'connected';
    }

    return 'not connected';
  }
  /**
   * Send a message to the server.
   *
   * @param {String} channel
   * @param {Object} value
   */


  send(channel, value) {
    const msg = JSON.stringify({
      'channel': channel,
      'payload': value
    });

    if (socket.readyState != 1) {
      this.pending.push(msg);
      return;
    }

    socket.send(msg);
  }

}

window.customElements.define('redwood-events', RedwoodEvents);