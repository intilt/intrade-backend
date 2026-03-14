import logging
from flask.views import MethodView
from flask import request, redirect

from core.Controller import Controller 

class BrokerLoginAPI(MethodView):
  def get(self, broker_name):
    redirectUrl = Controller.handleBrokerLogin(request.args, broker_name)
    return redirect(redirectUrl, code=302)

  def post(self, broker_name):
    redirectUrl = Controller.handleBrokerLogin(request.form, broker_name)
    return redirect(redirectUrl, code=302)