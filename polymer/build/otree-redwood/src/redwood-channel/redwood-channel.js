import { html, PolymerElement } from "../../node_modules/@polymer/polymer/polymer-element.js";
import '../redwood-events/redwood-events.js';
/*

`<redwood-channel>` lets you send and receive events on a given channel. This works
in conjunction with the groups from otree-redwood.

For example, let's say we want to let subjects send and receive orders on the
"orders" channel:

In your models.py:

```python
from otree_redwood.models import Group as RedwoodGroup

class Group(RedwoodGroup):

	def _on_orders_event(self, event=None, **kwargs):
		# probably should verify the event.participant has enough balance/units
		# to send the order

		# broadcast the order out to all subjects
		self.send("orders", event.value)
```

In your page template:

```html
<redwood-channel
	id="ordersChannel"
	channel="orders">
</redwood-channel>

<button on-click="sendOrder">Send Order</button>
```

```javascript
// some fake order we're going to send when the button is clicked
var fakeOrder = {
	'type': 'bid',
	'price': 5,
	'quantity': 2
}

var ordersChan = document.getElementbyId('ordersChannel');

// send the order out
function sendOrder() {
	ordersChan.send(fakeOrder);
}

// receive orders from the server
ordersChan.addEventListener('event', function(event) {
	console.log(event.detail.channel); // "orders"
	console.log(event.detail.timestamp);
	console.log(event.detail.payload); // fakeOrder, above
});
```

https://otree-redwood.readthedocs.io/webcomponents.html

*/

class RedwoodChannel extends PolymerElement {
  static get properties() {
    return {
      /* Channel to send/receive messages on. */
      channel: {
        type: String
        /**
         * Fired when a message is received on the channel.
         *	 
         * @event event
         * @param {event} otree_redwood.models.Event.message
         */

      }
    };
  }

  static get template() {
    return html`
            <redwood-events id="events" on-event="_handleEvent">
            </redwood-events>
        `;
  }

  _handleEvent(event) {
    if (event.detail.channel === this.channel) {
      this.dispatchEvent(new CustomEvent('event', {
        detail: event.detail,
        bubbles: true,
        composed: true
      }));
    }
  }
  /**
   * Send a message on the channel.
   *
   * @param {Object} payload
   */


  send(payload) {
    this.$.events.send(this.channel, payload);
  }

}

window.customElements.define('redwood-channel', RedwoodChannel);