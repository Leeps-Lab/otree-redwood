import { html, PolymerElement } from "../../node_modules/@polymer/polymer/polymer-element.js";
/*

`<otree-constants>` binds oTree template variables to itself.

It's useful to have an easy way to access oTree template variables in JavaScript
without double-curly brackets everywhere (e.g. "{{ }}"). Also, using JavaScript
variables makes it possible to test your JavaScript in a more isolated way than
running a full experiment.

`<otree-constants>` requires you to use a special template to instantiate all of its fields.
All this means is that any template that uses otree-redwood should inherit from `otree_redwood/Page.html`.

https://otree-redwood.readthedocs.io/webcomponents.html

*/

class OtreeConstants extends PolymerElement {
  static get properties() {
    return {
      /** Object containing info about the group this player is in.
        group.pk is the group object's primary key
        group.players is an array of objects with player code, role, id in group and payoff
        for each player in the group
        */
      group: {
        type: Object,
        notify: true,
        readonly: true,
        value: () => {
          return oTree.group;
        }
      },

      /** Player's role, e.g. {{ player.role }} */
      role: {
        type: String,
        notify: true,
        readonly: true,
        value: () => {
          return oTree.role;
        }
      },

      /** Participant's unique subject code,
          e.g. {{ player.participant.code }}
      */
      participantCode: {
        type: String,
        notify: true,
        readonly: true,
        value: () => {
          return oTree.participantCode;
        }
      },

      /** Current app name, e.g. {{ subsession.app_name }} */
      appName: {
        type: String,
        notify: true,
        readonly: true,
        value: () => {
          return oTree.appName;
        }
      },

      /** Player's index in group. e.g. {{ player.id_in_group }} */
      idInGroup: {
        type: String,
        notify: true,
        readonly: true,
        value: () => {
          return oTree.idInGroup;
        }
      },

      /** Player's role. e.g. {{ player.role }} */
      role: {
        type: String,
        notify: true,
        readonly: true,
        value: () => {
          return oTree.role;
        }
      },

      /** {{ csrf_token }} */
      csrfToken: {
        type: String,
        notify: true,
        readonly: true,
        value: () => {
          return oTree.csrf_token;
        }
      },

      /** True if the DEBUG environment variable is set. */
      debug: {
        type: Boolean,
        notify: true,
        readonly: true,
        value: () => {
          return oTree.debug;
        }
      }
    };
  }

}

window.customElements.define('otree-constants', OtreeConstants);