
typedef SessionExpiredCallback = void Function();

class SessionCoordinator {
  SessionExpiredCallback? onSessionExpired;

  void notifySessionExpired() {
    onSessionExpired?.call();
  }
}
