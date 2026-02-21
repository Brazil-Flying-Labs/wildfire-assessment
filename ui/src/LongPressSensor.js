/**
 * Custom dnd-kit sensor for touch drag with long press.
 *
 * Unlike the built-in TouchSensor, this uses PASSIVE touchmove listeners
 * during the delay period so the browser can still scroll normally.
 * Non-passive listeners are only added after the long press activates.
 */
class LongPressSensor {
  static activators = [
    {
      eventName: "onTouchStart",
      handler: ({ nativeEvent: event }, { onActivation }) => {
        if (event.touches.length > 1) return false;
        onActivation?.({ event });
        return true;
      },
    },
  ];

  constructor(props) {
    this.props = props;
    this.activated = false;
    this.autoScrollEnabled = true;

    const touch = props.event.touches?.[0];
    if (!touch) {
      props.onCancel();
      return;
    }

    this.initialCoords = { x: touch.clientX, y: touch.clientY };

    const { delay = 200, tolerance = 5 } =
      props.options?.activationConstraint ?? {};

    this._onEarlyMove = (e) => {
      const t = e.touches[0];
      if (!t) return;
      if (
        Math.abs(t.clientX - this.initialCoords.x) > tolerance ||
        Math.abs(t.clientY - this.initialCoords.y) > tolerance
      ) {
        this._abort();
      }
    };
    this._onEarlyEnd = () => this._abort();

    document.addEventListener("touchmove", this._onEarlyMove, {
      passive: true,
    });
    document.addEventListener("touchend", this._onEarlyEnd);
    document.addEventListener("touchcancel", this._onEarlyEnd);

    this._timer = setTimeout(() => this._activate(), delay);
  }

  _activate() {
    this._cleanupEarly();
    this.activated = true;
    this.props.onStart(this.initialCoords);

    this._onActiveMove = (e) => {
      if (e.cancelable) e.preventDefault();
      const t = e.touches[0];
      if (t) this.props.onMove({ x: t.clientX, y: t.clientY });
    };
    this._onActiveEnd = () => {
      this._cleanupActive();
      this.props.onEnd();
    };
    this._onActiveCancel = () => {
      this._cleanupActive();
      this.props.onCancel();
    };

    document.addEventListener("touchmove", this._onActiveMove, {
      passive: false,
    });
    document.addEventListener("touchend", this._onActiveEnd);
    document.addEventListener("touchcancel", this._onActiveCancel);
  }

  _abort() {
    this._cleanupEarly();
    this.props.onCancel();
  }

  _cleanupEarly() {
    if (this._timer) {
      clearTimeout(this._timer);
      this._timer = null;
    }
    document.removeEventListener("touchmove", this._onEarlyMove);
    document.removeEventListener("touchend", this._onEarlyEnd);
    document.removeEventListener("touchcancel", this._onEarlyEnd);
  }

  _cleanupActive() {
    document.removeEventListener("touchmove", this._onActiveMove);
    document.removeEventListener("touchend", this._onActiveEnd);
    document.removeEventListener("touchcancel", this._onActiveCancel);
  }
}

export default LongPressSensor;
