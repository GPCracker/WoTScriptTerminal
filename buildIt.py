import io
import os
import imp
import json
import time
import shutil
import struct
import marshal
import zipfile
import traceback

def compile_script(script, filename='<string>', filetime=time.time()):
	with io.BytesIO() as binary_buffer:
		binary_buffer.write(imp.get_magic())
		binary_buffer.write(struct.pack('<I', int(filetime)))
		binary_buffer.write(marshal.dumps(compile(script, filename, 'exec')))
		result = binary_buffer.getvalue()
	return result

def join_path(*args, **kwargs):
	path = os.path.normpath(os.path.join(*args, **kwargs)).replace(os.sep, '/')
	return path + ('/' if os.path.isdir(path) else '')

def replace_macros(string, macros_list):
	for macros, value in macros_list:
		string = string.replace(macros, value)
	return string

def files_iterator(src_list, source_path='./'):
	for source, build, release in src_list:
		_source = join_path(source_path, source)
		if os.path.isfile(_source):
			yield join_path(source), join_path(build), join_path(release)
		elif os.path.isdir(_source):
			for root, dirs, files in os.walk(_source):
				root = os.path.relpath(root, _source)
				for sfile in files:
					yield join_path(source, root, sfile), join_path(build, root, sfile), join_path(release, root, sfile)
	return

def process_source(source, build, release, fzip, source_path='./', build_path='./build/', zip_path='./', compile_source=False, version=None):
	src_file = join_path(source_path, source)
	dst_file = join_path(build_path, build)
	zip_file = join_path(zip_path, release)
	if compile_source and os.path.splitext(dst_file)[1] == '.py':
		dst_file = os.path.splitext(dst_file)[0] + '.pyc'
	if compile_source and os.path.splitext(zip_file)[1] == '.py':
		zip_file = os.path.splitext(zip_file)[0] + '.pyc'
	print '{0} --> {1}'.format(src_file, dst_file)
	if not os.path.isdir(os.path.dirname(dst_file)):
		os.makedirs(os.path.dirname(dst_file))
	with open(src_file, 'rt') as fobj:
		script = fobj.read()
	if version is not None:
		script.replace(*version)
	with open(dst_file, 'wb' if compile_source else 'wt') as fobj:
		fobj.write(compile_script(script, source, os.path.getmtime(src_file)) if compile_source else script)
	fzip.write(dst_file, zip_file)
	return

def process_resource(resource, build, release, fzip, resource_path='./', build_path='./build/', zip_path='./'):
	src_file = join_path(resource_path, resource)
	dst_file = join_path(build_path, build)
	zip_file = join_path(zip_path, release)
	print '{0} --> {1}'.format(src_file, dst_file)
	if not os.path.isdir(os.path.dirname(dst_file)):
		os.makedirs(os.path.dirname(dst_file))
	with open(src_file, 'rb') as fobj:
		data = fobj.read()
	with open(dst_file, 'wb') as fobj:
		fobj.write(data)
	fzip.write(dst_file, zip_file)
	return

if __name__ == '__main__':
	try:
		cfg_file = join_path(os.path.splitext(__file__)[0] + '.cfg')
		with open(cfg_file, 'rb') as f:
			config = json.loads(f.read())
		vcs_file = join_path(os.path.dirname(__file__), 'version.cfg')
		version = '<custom_build>'
		if os.path.isfile(vcs_file):
			with open(vcs_file, 'r+b') as f:
				vcs_info = json.load(f)
				version = '{release}#{next_build}'.format(**vcs_info)
				vcs_info["next_build"] += 1
				f.seek(0)
				f.truncate()
				f.write(json.dumps(vcs_info) + '\n')
		for module_config in config["modules"]:
			module_config["path_macros"].append([u"<application>", config["application"]])
			module_config["source_path"] = replace_macros(module_config["source_path"], module_config["path_macros"])
			module_config["resource_path"] = replace_macros(module_config["resource_path"], module_config["path_macros"])
			module_config["build_path"] = replace_macros(module_config["build_path"], module_config["path_macros"])
			module_config["release_path"] = replace_macros(module_config["release_path"], module_config["path_macros"])
			module_config["zip_path"] = replace_macros(module_config["zip_path"], module_config["path_macros"])
			if os.path.isdir(module_config["build_path"]):
				shutil.rmtree(module_config["build_path"])
			if os.path.isfile(module_config["release_path"]):
				os.remove(module_config["release_path"])
			if not os.path.isdir(module_config["build_path"]):
				os.makedirs(module_config["build_path"])
			if not os.path.isdir(os.path.dirname(module_config["release_path"])):
				os.makedirs(os.path.dirname(module_config["release_path"]))
			with zipfile.ZipFile(join_path(module_config["release_path"]), 'w', zipfile.ZIP_DEFLATED) as fzip:
				for source, build, release in files_iterator(module_config["sources"], module_config["source_path"]):
					process_source(source, build, release, fzip, module_config["source_path"], module_config["build_path"], module_config["zip_path"], module_config["compile_sources"], (config["version_macros"], version))
				for resource, build, release in files_iterator(module_config["resources"], module_config["resource_path"]):
					process_resource(resource, build, release, fzip, module_config["resource_path"], module_config["build_path"], module_config["zip_path"])
	except:
		traceback.print_exc()
