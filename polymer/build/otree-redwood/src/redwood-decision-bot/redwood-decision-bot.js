import { html, PolymerElement } from "../../node_modules/@polymer/polymer/polymer-element.js";
import '../otree-constants/otree-constants.js';
import '../redwood-period/redwood-period.js';
/*

`<redwood-decision-bot>` is useful for testing - it randomly sets the player's
decision in redwood-decision to a numeric value.

https://otree-redwood.readthedocs.io/webcomponents.html

*/

class RedwoodDecisionBot extends PolymerElement {
  static get properties() {
    return {
      myDecision: {
        type: Number,
        notify: true
      },
      otherDecision: {
        type: Number
      },
      direction: {
        type: String
      },
      running: {
        type: Boolean
      },
      velocity: {
        type: Number,
        value: 0.1
      },
      lambda: {
        type: Number,
        value: 0.1
      },
      pattern: {
        type: Boolean,
        value: false
      },
      // set by redwood-period
      _isPeriodRunning: {
        type: Boolean,
        observer: '_isPeriodRunningChanged'
      }
    };
  }

  static get template() {
    return html`
            <otree-constants id="constants" debug="{{ debug }}">
            </otree-constants>
            <redwood-period running="{{ _isPeriodRunning }}">
            </redwood-period>
            <template is="dom-if" if="[[ debug ]]">
                <div class="well">
                    <p>Continuous Decision Bot</p>
                    <p>Direction of max payoff: [[ direction ]]</p>
                    <p>
                        <label>Velocity</label>
                        <input type="number" min="0" max="1" step=".01" value="{{ velocity::input }}" class="self-end">
                    </p>
                    <p>
                        <label>Lambda</label>
                        <input type="number" min="0" max="1" step=".01" value="{{ lambda::input }}" class="self-end">
                    </p>
                    <p>
                        <button type="button" on-click="togglePattern" hidden$="[[ !pattern ]]">Gradient</button>
                        <button type="button" on-click="togglePattern" hidden$="[[ pattern ]]">Pattern</button>
                    </p>
                    <p>
                        <button type="button" on-click="stop" hidden$="[[ !running ]]">Stop</button>
                        <button type="button" on-click="start" hidden$="[[ running ]]">Start</button>
                    </p>
                </div>
            </template>
        `;
  }

  start() {
    this.running = true;
    setTimeout(this._updateDecision.bind(this), this._nextDecisionInterval());
  }

  stop() {
    this.running = false;
  }

  togglePattern() {
    this.pattern = !this.pattern;
  }

  _isPeriodRunningChanged() {
    if (this.debug && this._isPeriodRunning) {
      this.start();
    } else {
      this.stop();
    }
  }

  _updateDecision() {
    if (this.pattern) {
      this._updateDecisionWithPattern();
    } else {
      this._updateDecisionWithGradient();
    }
  }

  _updateDecisionWithPattern() {
    if (this.myDecision == null || isNaN(this.myDecision)) {
      this.myDecision = this.lambda;
    } else if (Math.abs(this.myDecision - this.lambda) < 0.1) {
      this.myDecision = 1 - this.lambda;
    } else {
      this.myDecision = this.lambda;
    }

    if (this.running) {
      setTimeout(this._updateDecision.bind(this), 500);
    }
  }

  _updateDecisionWithGradient() {
    if (Math.random() < this.lambda || this.myDecision == null || this.otherDecision == null || isNaN(this.myDecision) || isNaN(this.otherDecision)) {
      this.myDecision = Math.random();
    } else {
      const currPayoff = this.payoffFunction(this.myDecision, this.otherDecision);
      const up = Math.min(this.myDecision + this.velocity * Math.random(), 1);
      const down = Math.max(this.myDecision - this.velocity * Math.random(), 0);
      const upPayoff = this.payoffFunction(up, this.otherDecision);
      const downPayoff = this.payoffFunction(down, this.otherDecision);

      if (upPayoff > currPayoff) {
        this.myDecision = up;
        this.direction = 'up';
      } else if (downPayoff > currPayoff) {
        this.myDecision = down;
        this.direction = 'down';
      } else {
        this.direction = 'none';
      }
    }

    if (this.running) {
      setTimeout(this._updateDecision.bind(this), this._nextDecisionInterval());
    }
  }

  _nextDecisionInterval() {
    const max = 1000;
    const min = 100;
    return Math.floor(Math.random() * (max - min)) + min;
  }

}

window.customElements.define('redwood-decision-bot', RedwoodDecisionBot);