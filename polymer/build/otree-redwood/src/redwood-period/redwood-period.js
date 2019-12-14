import { html, PolymerElement } from "../../node_modules/@polymer/polymer/polymer-element.js";
import '../redwood-channel/redwood-channel.js';
/*

`<redwood-period>` listens for period-start and period-end events on the
"state" channel. When the `period-end` event is seen, it automatically moves
players on to the next oTree page.

https://otree-redwood.readthedocs.io/webcomponents.html

*/

class RedwoodPeriod extends PolymerElement {
  static get properties() {
    return {
      /**
       * true after the period_start message has been received and
       * before the period_end message has been received.
       */
      running: {
        type: Boolean,
        value: false,
        notify: true
        /**
         * Fired when the `period_start` message is received.
         * 
         * @event period-start
         */

        /**
         * Fired when the `period_end` message is received.
         *	 
         * @event period-end
         */

      }
    };
  }

  static get template() {
    return html`
            <redwood-channel channel="state" on-event="_handleStateEvent">
            </redwood-channel>
        `;
  }

  _handleStateEvent(event) {
    const state = event.detail.payload;

    if (state == 'period_start') {
      this.running = true;
      this.dispatchEvent(new CustomEvent('period-start'));
    } else if (state == 'period_end') {
      this.running = false;
      this.dispatchEvent(new CustomEvent('period-end'));
      const xhr = new XMLHttpRequest();
      xhr.open('POST', '', true);
      xhr.setRequestHeader('X-CSRFToken', oTree.csrfToken);
      xhr.send('');
      window.setTimeout(() => {
        window.location = window.location;
      }, 1000);
    }
  }

}

window.customElements.define('redwood-period', RedwoodPeriod);