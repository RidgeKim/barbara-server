from flask import render_template, redirect, session, url_for, request, jsonify
from werkzeug import secure_filename
from os import path, remove

from barbara import app, db

from barbara.models.users import User
from barbara.models.user_preferences import UserPreference
from barbara.models.investment_plans import InvestmentPlan

from oxford.speaker_recognition.Verification.CreateProfile import create_profile
from oxford.speaker_recognition.Verification.EnrollProfile import enroll_profile
from oxford.speaker_recognition.Verification.VerifyFile import verify_file

VERIFICATION_RESULT_ACCEPT = 'Accept'
VERIFICATION_CONFIDENCE = ['Low', 'Normal', 'High']


@app.route("/users")
def view_users():
    all_users = User.query.order_by(User.first_name.asc()).all()
    return render_template('users.html', users=all_users)


@app.route("/login", methods=['GET', 'POST'])
def login_user():
    if request.method == 'POST':
        _username = request.form['username']
        _password = request.form['password']
        user = User.query.filter_by(username=_username).first()
        if user and user.check_password(_password):
            session['user'] = user.to_dict()
            return redirect(url_for('home'))
        else:
            return render_template("login-form.html", error='Invalid user credentials!!')
    else:
        return render_template("login-form.html")


@app.route("/logout")
def logout_user():
    if session.get('user', None):
        session.clear()
    return redirect(url_for('home'))


@app.route("/enroll-voice", methods=['POST', 'GET'])
def voice_register():
    _is_post_response = None
    _success = False
    # print_all_profiles(app.config['MICROSOFT_SPEAKER_RECOGNITION_KEY'])
    if request.method == 'POST':
        # receive voice file from request
        if session.get('user', None):
            _is_post_response = True
            _user_id = session['user']['id']
            user = User.query.filter_by(id=_user_id).first()
            _file = request.files['file']
            if _file and user:
                filename = secure_filename(_file.filename)
                # print app.config['UPLOAD_FOLDER']
                _created_file_path = path.join(app.config['UPLOAD_FOLDER'], filename)
                _file.save(_created_file_path)
                # print app.config['MICROSOFT_SPEAKER_RECOGNITION_KEY']
                # print user.speaker_profile_id
                # print _created_file_path
                try:
                    enroll_profile(app.config['MICROSOFT_SPEAKER_RECOGNITION_KEY'], user.speaker_profile_id,
                                   _created_file_path)
                    _success = True
                except Exception:
                    _success = False
                remove(_created_file_path)
            # register with the current user's speaker profile
            return render_template('post-voice.html', is_post_response=_is_post_response, success=_success)
    else:
        return render_template('post-voice.html')


@app.route("/verify-voice", methods=['POST', 'GET'])
def user_voice_verify():
    _is_post_response = None
    _success = False
    # print_all_profiles(app.config['MICROSOFT_SPEAKER_RECOGNITION_KEY'])
    if request.method == 'POST':
        # receive voice file from request
        if session.get('user', None):
            _is_post_response = True
            _user_id = session['user']['id']
            user = User.query.filter_by(id=_user_id).first()
            _file = request.files['file']
            if _file and user:
                filename = secure_filename(_file.filename)
                # print app.config['UPLOAD_FOLDER']
                _created_file_path = path.join(app.config['UPLOAD_FOLDER'], filename)
                _file.save(_created_file_path)
                print app.config['MICROSOFT_SPEAKER_RECOGNITION_KEY']
                print user.speaker_profile_id
                print _created_file_path
                try:
                    verification_response = verify_file(app.config['MICROSOFT_SPEAKER_RECOGNITION_KEY'],
                                                        _created_file_path,
                                                        user.speaker_profile_id)
                    _index = VERIFICATION_CONFIDENCE.index(verification_response.get_confidence())
                    _success = VERIFICATION_RESULT_ACCEPT == verification_response.get_result()
                    _success = _success and (_index != -1)
                except Exception:
                    _success = False
                remove(_created_file_path)
            # register with the current user's speaker profile
            return render_template('post-voice.html', is_post_response=_is_post_response, success=_success)
    else:
        return render_template('post-voice.html')


@app.route("/api/users/verify-voice", methods=['POST'])
def user_voice_verification():
    # print_all_profiles(app.config['MICROSOFT_SPEAKER_RECOGNITION_KEY'])
    # receive voice file from request
    _user_id = request.form['userId']
    _file = request.files['file']
    user = User.query.filter_by(id=_user_id).first()
    _success = True
    _response_item = None
    if _file and user:
        filename = secure_filename(_file.filename)
        # print app.config['UPLOAD_FOLDER']
        _created_file_path = path.join(app.config['UPLOAD_FOLDER'], filename)
        _file.save(_created_file_path)
        # print app.config['MICROSOFT_SPEAKER_RECOGNITION_KEY']
        # print user.speaker_profile_id
        # print _created_file_path
        try:
            verification_response = verify_file(app.config['MICROSOFT_SPEAKER_RECOGNITION_KEY'], _created_file_path,
                                                user.speaker_profile_id)
            _index = VERIFICATION_CONFIDENCE.index(verification_response.get_confidence())
            _success = VERIFICATION_RESULT_ACCEPT == verification_response.get_result()
            _success = _success and (_index != -1)
        except Exception:
            # _success = False
            pass
        remove(_created_file_path)
        _response_item = user.to_dict()
    # register with the current user's speaker profile
    return jsonify(success=_success, item=_response_item)


@app.route("/my-profile")
def my_profile():
    if session.get('user', None):
        _user_info = User.query.filter_by(id=session['user']['id']).first()
        return render_template('my-profile.html', user=_user_info)
    return 'Not logged In', 401


@app.route("/api/users/all")
def get_users():
    all_users = User.query.order_by(User.first_name.asc()).all()
    result = [user.to_dict() for user in all_users]
    return jsonify(items=result, success=True)


@app.route("/api/users/add", methods=['POST'])
def add_user():
    _first_name = request.form['firstName']
    _last_name = request.form['lastName']
    _username = request.form['username']
    _password = request.form['password']
    _wallet = request.form['wallet']
    _currency_type = request.form['currencyType']
    _speaker_profile_id = create_profile(app.config['MICROSOFT_SPEAKER_RECOGNITION_KEY'], app.config['DEFAULT_LOCALE'])
    # request.form['speakerProfileId']
    _credit = 0
    new_user = User(first_name=_first_name, last_name=_last_name,
                    username=_username, password=_password, wallet=_wallet,
                    credit=_credit, currency_type=_currency_type,
                    speaker_profile_id=_speaker_profile_id)
    db.session.add(new_user)
    db.session.commit()
    return jsonify(success=True, item=new_user.to_dict())


@app.route("/api/users/save-preferences", methods=['POST'])
def save_user_preferences():
    _user_id = request.form['userId']
    _budget = request.form['budget']
    _security_question = request.form['securityQuestion']
    _nick_name = request.form['nickName']
    if _user_id:
        user_preference = UserPreference.query.filter_by(user_id=_user_id).first()
        if not user_preference:
            user_preference = UserPreference(user_id=_user_id)
            db.session.add(user_preference)
        if _budget:
            user_preference.budget = float(_budget)
        if _nick_name:
            user_preference.nick_name = _nick_name
        if _security_question:
            user_preference.security_question = _security_question
        db.session.commit()
        return jsonify(success=True, item=user_preference.to_dict())
    return jsonify(success=False, item=None)


@app.route("/api/users/preferences", methods=['GET'])
def get_user_preferences():
    _user_id = request.args['userId']
    if _user_id:
        user_preference = UserPreference.query.filter_by(user_id=_user_id).first()
        if not user_preference:
            user_preference = UserPreference(user_id=_user_id)
        return jsonify(success=True, item=user_preference.to_dict())
    return jsonify(success=False, item=None)


@app.route("/api/login", methods=['POST'])
def login():
    _username = request.form['username']
    _password = request.form['password']
    user = User.query.filter_by(username=_username).first()
    if user and user.check_password(_password):
        return jsonify(success=True, item=user.to_dict())
    else:
        return jsonify(success=False, error='Invalid user credentials!!')


@app.route("/investment-plans", methods=['GET'])
def investment_plans():
    _plans = InvestmentPlan.query.all()
    return render_template('investment-plans.html', plans=_plans)


@app.route("/investment-plans/add", methods=['GET', 'POST'])
def add_investment_plan():
    if request.method == 'POST':
        _description = request.form['description']
        _amount = request.form['amount']
        _type = request.form['type']
        new_plan = InvestmentPlan(description=_description, amount=_amount, type=_type)
        db.session.add(new_plan)
        db.session.commit()
        return redirect(url_for('investment_plans'))
    return render_template('new-investment-plan.html')


@app.route("/api/investment/plans", methods=['GET'])
def get_investment_plans():
    _plans = InvestmentPlan.query.all()
    _plans = [plan.to_dict() for plan in _plans]
    return jsonify(success=True, items=_plans)
