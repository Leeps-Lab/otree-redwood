import { html, PolymerElement } from "../../node_modules/@polymer/polymer/polymer-element.js";
import '../otree-constants/otree-constants.js';
import '../redwood-channel/redwood-channel.js';
/*

`<redwood-decision>` makes it easy to handle a single decision variable that
each player can set. The decision variable can be a number, boolean, string,
or even an Object. At any given point in time each player only has one value
for their decision forming a set of decisions for the group.

https://otree-redwood.readthedocs.io/webcomponents.html

*/

class RedwoodDecision extends PolymerElement {
  static get properties() {
    return {
      /* Initial decision the player starts with */
      initialDecision: {
        type: Object
      },

      /**
       * Map from participant code to decision variable
       *
       * e.g. if there are two participants, `n282bsh4` and
       * `s7zznoq4` and numeric decisions, this might be:
       * ```javascript
       * {
       *   "s7zznoq4": 10,
       *   "n282bsh4": 20
       * }
       * ```
       */
      groupDecisions: {
        type: Object,
        readonly: true,
        notify: true,
        value: () => {
          return {};
        }
      },

      /**
       * Your decision.
       *
       * When set, this will send a message to the server. Once the
       * server sends out the `group_decisions` message, the change
       * will be reflected in `myCurrentDecision`.
       */
      myDecision: {
        type: Object,
        notify: true,
        observer: '_myDecisionChanged'
      },

      /* Your decision according to the server. */
      myCurrentDecision: {
        type: Object,
        readonly: true,
        notify: true
      },

      /* A utility - if there are 2 players in the group, this is
       * the decision value of the other player.
       */
      otherDecision: {
        type: Object,
        readonly: true,
        notify: true,
        computed: '_computeOtherDecision(groupDecisions.*)'
      },

      /* Sets a rate-limit on the number of times you can change
       * `myDecision` in one second.
       */
      maxPerSecond: {
        type: Number,
        value: 0
      },
      _queries: {
        type: Array,
        value: () => {
          const a = [];

          for (let i = 0; i < 60; i++) {
            a.push(0);
          }

          return a;
        }
      }
    };
  }

  static get template() {
    return html`
            <otree-constants id="constants"></otree-constants>
            <redwood-channel id="decisionsChannel" channel="decisions">
            </redwood-channel>
            <redwood-channel channel="group_decisions" on-event="_handleGroupDecisionsEvent">
            </redwood-channel>
        `;
  }

  ready() {
    super.ready();
    this.myDecision = this.initialDecision;
  }

  _handleGroupDecisionsEvent(event) {
    this.groupDecisions = event.detail.payload;
    const pcode = this.$.constants.participantCode;
    this.myCurrentDecision = this.groupDecisions[pcode];

    if (this.myDecision === null) {
      this.myDecision = this.groupDecisions[pcode];
    }

    this.dispatchEvent(new CustomEvent('group-decisions-changed'));
  }

  _computeOtherDecision(groupDecisionsChange) {
    const groupDecisions = groupDecisionsChange.value;
    if (!groupDecisions) return null;
    const pcode = this.$.constants.participantCode;

    for (let key in groupDecisions) {
      if (key != pcode) {
        return groupDecisions[key];
      }
    }

    return null;
  }

  _rate() {
    const s = new Date().getSeconds();
    this._queries[s]++;
    let last = s - 1;

    if (last < 0) {
      last = this._queries.length - 1;
    }

    this._queries[last] = 0;
    return this._queries[s];
  }

  _myDecisionChanged() {
    if (this.maxPerSecond > 0 && this._rate() > this.maxPerSecond) {
      console.warn('rate limited'); // TODO: retry latest decision after rate goes down.

      return;
    }

    this.$.decisionsChannel.send(this.myDecision);
  }

}

window.customElements.define('redwood-decision', RedwoodDecision);